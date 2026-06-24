# Chat Flow

이 문서는 현재 구현 기준으로 `POST /api/v1/ai/chat` 요청이 어떤 순서로 처리되는지 설명한다.

기준 파일:

- `backend/app/api/routes/ai_gateway.py`
- `backend/app/agents/leader.py`
- `backend/app/agents/memory.py`
- `backend/app/agents/long_term_memory.py`
- `backend/app/agents/agent_registry.py`
- `backend/app/agents/services/*`
- `backend/app/tools/tool_gateway.py`
- `backend/app/trace/*`

---

## 전체 흐름

```text
User / Frontend
  -> POST /api/v1/ai/chat
  -> AI Gateway
  -> LeaderAgent.run()
     1. Short Memory Load
     2. Long-term Memory Load
     3. Pending Clarification Check
     4. Intent Analysis
     5. Concept Resolution
     6. Agent Routing
     7. Missing Slot Clarification Check
     8. Execution Step Build
     9. Sub-Agent / Tool Execution
    10. Evidence Save + Link
    11. Execution Plan Finalize
    12. Result Re-ranking
    13. Answer Compose
    14. Validation / Sanitization
    15. Short Memory Save
    16. Long-term Memory Save
    17. LeaderDecision Save
    18. decision_v2 Build
  -> ChatResponse
```

---

## 1. Entry Point

엔드포인트:

- `POST /api/v1/ai/chat`

구현 파일:

- [ai_gateway.py](/C:/temp/core-banking/backend/app/api/routes/ai_gateway.py)

입력 스키마:

```json
{
  "message": "신용대출 금리 알려줘",
  "session_id": "demo-session-1",
  "channel": "web",
  "user_id": null
}
```

주요 처리:

- `request_id` 생성
- `REQUEST_RECEIVED` trace 기록
- `LeaderAgent.run(...)` 호출
- 완료 후 `RESPONSE_COMPLETED` trace 기록
- `trace_count`, `evidence_count`를 계산해서 응답에 포함

권한:

- `require_analyst_context` 적용
- `AUTH_ENABLED=false`면 개발 환경에서 사실상 관리자처럼 동작

---

## 2. ChatRequest / ChatResponse

스키마 파일:

- [ai_gateway.py](/C:/temp/core-banking/backend/app/schemas/ai_gateway.py)

응답 주요 필드:

- `request_id`
- `message`
- `plan`
- `results`
- `answer`
- `intent`
- `memory_turns`
- `trace_count`
- `evidence_count`
- `decision_v2`
- `needs_clarification`
- `clarification_question`

즉, 현재 채팅 응답은 단순 답변 문자열만 반환하는 것이 아니라 실행 계획과 추적 메타데이터도 함께 반환한다.

---

## 3. Short Memory Load

구현 파일:

- [memory.py](/C:/temp/core-banking/backend/app/agents/memory.py)

동작:

- Redis에서 `session:{session_id}:history` 조회
- 최근 대화 턴을 리스트 형태로 복원
- 최대 5턴까지 유지
- Redis TTL은 3600초

Leader 처리:

- `history = load_history(session_id)`
- `memory_turns = len(history) // 2`
- `MEMORY_LOADED` trace 기록

세션 ID가 없거나 Redis가 실패하면 빈 히스토리로 계속 진행한다.

---

## 4. Long-term Memory Load

구현 파일:

- [long_term_memory.py](/C:/temp/core-banking/backend/app/agents/long_term_memory.py)

동작:

- PostgreSQL의 장기 메모리 레코드 조회
- `user_id`가 있으면 사용자 기준, 없으면 `session_id` 기준 fallback
- 최근 최대 5건 로드
- 각 항목에는 `intent`, `concepts`, `keywords`, `question`, `answer` 요약이 포함

Leader 처리:

- `load_long_term_history(db, session_id, user_id=owner_name)`
- `LTM_LOADED` trace 기록

---

## 5. Pending Clarification Check

구현 파일:

- `backend/app/agents/services/clarification_service_adapter.py`
- `backend/app/agents/leader.py`

동작:

- 같은 `session_id`에 미해결 clarification이 있으면 먼저 해소를 시도한다.
- 사용자의 추가 입력이 보충 답변으로 판단되면 원 질문과 합쳐서 계속 처리한다.
- 아직 정보가 부족하면 clarification 질문을 그대로 반환한다.

이 경우 응답 특징:

- `needs_clarification = true`
- `clarification_question` 포함
- `plan.steps`는 비어 있을 수 있음

또한 clarification 질문도 short memory에 저장한다.

---

## 6. Intent Analysis

구현 파일:

- [leader.py](/C:/temp/core-banking/backend/app/agents/leader.py)

핵심 메서드:

- `_analyze_intent(...)`

동작:

- 현재 질문
- short memory
- long-term memory

를 바탕으로 다음 정보를 만든다.

- `intent`
- `keywords`
- 추가 분석 필드

Trace:

- `INTENT_ANALYZED`

참고:

- `OPENAI_API_KEY`가 없으면 일부 분석은 fallback 경로로 동작할 수 있다.

---

## 7. Concept Resolution

구현 파일:

- `backend/app/agents/services/concept_resolution_service.py`
- `backend/app/knowledge/concept_service.py`
- `backend/app/agents/leader.py`

동작:

- 질문과 intent keyword를 기반으로 direct concept 탐지
- 필요 시 relation / synonym 기반 concept 확장
- direct concept와 expanded concept를 분리해 관리

Leader 결과 변수:

- `detected`
- `all_concepts`
- `detected_set`

Trace:

- `CONCEPT_DETECTED`
- `detected_concepts`
- `expanded_concepts`
- `total_concepts`

---

## 8. Agent Routing

구현 파일:

- [agent_registry.py](/C:/temp/core-banking/backend/app/agents/agent_registry.py)
- `backend/app/agents/services/routing_policy.py`

동작:

1. `agent_concept_mapping` 기반 기본 라우팅
2. `RoutingPolicy`가 내부 rule로 보정
3. concept 분류 결과와 answer slot 후보 생성

중요 원칙:

- Agent는 LLM이 임의로 고르지 않는다.
- 기본 라우팅은 DB 매핑을 따른다.
- 현재 활성 Sub Agent는 `PRODUCT`, `RATE`, `POLICY`, `SEARCH`, `FOREX`, `NOTIFICATION`이다.

Trace:

- `AGENT_SELECTED`
- `routed_agents`
- `unrouted_concepts`

---

## 9. Missing Slot Clarification Check

라우팅 직후, 실행 전에 한 번 더 clarification 여부를 판단한다.

동작:

- 질문 의도에 비해 필요한 슬롯이 빠졌는지 점검
- 예를 들어 금액, 통화, 등급, 상품 유형 같은 정보가 부족하면 질문을 되묻는다

이 경로로 빠질 경우:

- Sub-Agent 실행 없이 종료될 수 있다
- `needs_clarification = true`
- clarification 질문이 short memory에 저장된다

---

## 10. Execution Step Build

구현 파일:

- `backend/app/agents/services/execution_planner.py`

동작:

- 라우팅 결과를 바탕으로 `ExecutionStep` 목록 생성
- 각 step은 `agent_id`, `concept_id`, `api_id`, `params`를 가진다
- 현재 질문에서 어떤 Tool을 실제로 칠지 결정하는 단계다

Leader 처리:

- `steps, seen_apis = self._execution_planner.build_steps(...)`
- 이후 `ExecutionPlan` 객체를 조립한다

---

## 11. Sub-Agent / Tool Execution

구현 파일:

- [leader.py](/C:/temp/core-banking/backend/app/agents/leader.py)
- `backend/app/agents/*.py`
- `backend/app/tools/tool_gateway.py`

동작:

- 라우팅된 각 Agent에 대해 해당 API 목록을 전달
- Agent는 `AgentInput`을 받아 `run()` 수행
- Agent 내부에서 ToolGateway를 통해 Mock API 호출
- 결과는 `StepResult` 리스트로 누적

현재 대표 Tool 범위:

- 대출: `MOCK_PRODUCT_LOOKUP`, `MOCK_RATE_LOOKUP`, `MOCK_POLICY_LOOKUP`
- 검색/자격: `MOCK_DOCUMENT_SEARCH`, `MOCK_ELIGIBILITY_CHECK`, `MOCK_COUNSELING_HISTORY`, `MOCK_BRANCH_LOOKUP`
- 금리 계산: `MOCK_RATE_SIMULATION`, `MOCK_PERSONALIZED_RATE_LOOKUP`
- 외환: `MOCK_EXCHANGE_RATE_LOOKUP`, `MOCK_CURRENCY_EXCHANGE_CALC`, `MOCK_FOREIGN_REMITTANCE`, `MOCK_FOREIGN_DEPOSIT_RATE`
- 알림: `MOCK_NOTIFICATION_RULES`, `MOCK_NOTIFICATION_SEND`

Trace:

- API 호출마다 `TOOL_INVOKED`

---

## 12. Evidence Save And Link

구현 파일:

- `backend/app/trace/evidence_service.py`
- `backend/app/trace/evidence_scorer.py`

동작:

- 성공한 Tool 결과는 evidence 후보로 저장
- `request_id`, `concept_id`, `source_id`, `agent_id`와 함께 점수화
- 이후 같은 요청 내 evidence를 `link_related_evidence(...)`로 연결

응답에서는 직접 evidence 본문이 오지 않지만 다음 필드는 제공된다.

- `evidence_count`

세부 evidence 조회 API:

- `GET /api/v1/ai/traces/{request_id}/evidence`

---

## 13. Execution Plan Finalize

실행이 끝난 뒤 Leader는 최종 `plan` 객체를 만든다.

포함 정보:

- `request_id`
- `message`
- `detected_concepts`
- `routed_agents`
- `steps`

Trace:

- `PLAN_CREATED`

주의:

- 코드상 `PLAN_CREATED`는 실제 step 실행 이후 기록되지만, 의미상으로는 이번 요청의 실행 계획 확정 이벤트로 볼 수 있다.

---

## 14. Result Re-ranking

구현 파일:

- `backend/app/agents/leader.py`

동작:

- raw Tool 결과를 intent와 질의 focus 기준으로 다시 정렬
- 특정 질문에서는 관련 없는 API 결과를 답변에서 약화 또는 제외
- 예: 환전 계산 질문에서는 일반 환율 목록보다 계산 결과를 우선

이 단계는 현재 별도 trace event 이름으로 직접 기록되지는 않지만, 최종 `results`는 rerank 이후 목록이다.

---

## 15. Answer Compose

구현 파일:

- `backend/app/agents/services/answer_composer.py`
- `backend/app/agents/leader.py`

동작:

- classified concept와 ranked result를 바탕으로 answer slot을 구성
- `self._summarize(...)`를 통해 최종 자연어 답변 생성
- short memory와 long-term memory가 답변 맥락에 반영될 수 있다

현재 응답의 `answer`는 이 단계 결과다.

---

## 16. Validation And Sanitization

구현 파일:

- `backend/app/agents/validator.py`

동작:

- 최종 답변과 evidence 결과를 바탕으로 안전성 / grounding / 권한 관련 검사를 수행
- 필요하면 `sanitized_answer`로 교체
- `risk_flags`, `actions_taken`, `requires_disclaimer`는 `decision_v2`에 반영

예:

- 참고용 안내 문구 추가
- 사용자 권한에 맞지 않는 표현 완화

---

## 17. Memory Save

### Short Memory Save

구현 파일:

- [memory.py](/C:/temp/core-banking/backend/app/agents/memory.py)

동작:

- `save_turn(session_id, message, answer)` 호출
- user / assistant 메시지를 쌍으로 저장
- 최근 5턴만 유지

주의:

- 현재 코드에서는 저장은 수행하지만 별도 `MEMORY_SAVED` trace를 직접 남기지는 않는다.

### Long-term Memory Save

구현 파일:

- [long_term_memory.py](/C:/temp/core-banking/backend/app/agents/long_term_memory.py)

동작:

- 질문/답변 요약을 장기 메모리로 저장
- `intent`, `detected_concepts`, `keywords`도 함께 남김
- 실패해도 채팅 응답 자체는 계속 반환된다

주의:

- 현재 코드에서는 저장은 수행하지만 별도 `LTM_SAVED` trace를 직접 남기지는 않는다.

---

## 18. LeaderDecision Save

구현 파일:

- `backend/app/models/trace_model.py`
- `backend/app/agents/leader.py`

동작:

- `LeaderDecision` 레코드 저장
- 핵심 저장 항목:
  - `detected_intent`
  - `detected_concepts`
  - `direct_concepts`
  - `expanded_concepts`
  - `selected_agents`
  - `confidence_score`
  - `total_steps`
  - `memory_turns`
  - `ltm_turns`
  - `answer`

이 정보는 trace 요약, decision 화면, 운영 분석 화면에서 사용된다.

---

## 19. decision_v2 Build

구현 파일:

- `backend/app/agents/leader.py`
- `backend/app/schemas/decision_trace.py`

동작:

- 현재 요청의 판단 과정을 구조화된 스키마로 묶는다
- 포함 정보:
  - context loaded
  - intent
  - concept 분류
  - decision rules applied
  - selected / rejected agents
  - execution strategy
  - answer slots
  - risk flags
  - disclaimer 여부

이 값은 채팅 응답의 `decision_v2` 필드로 직접 내려간다.

---

## 20. ChatResponse Example

```json
{
  "request_id": "uuid-xxxx",
  "message": "신용대출 금리 알려줘",
  "plan": {
    "request_id": "uuid-xxxx",
    "message": "신용대출 금리 알려줘",
    "detected_concepts": [
      "CONCEPT_PERSONAL_CREDIT_LOAN",
      "CONCEPT_INTEREST_RATE"
    ],
    "routed_agents": ["RATE_AGENT"],
    "steps": [
      {
        "step_index": 0,
        "agent_id": "RATE_AGENT",
        "concept_id": "CONCEPT_INTEREST_RATE",
        "api_id": "MOCK_RATE_LOOKUP",
        "params": {}
      }
    ]
  },
  "results": [
    {
      "step_index": 0,
      "api_id": "MOCK_RATE_LOOKUP",
      "status": "success",
      "data": {},
      "error": null
    }
  ],
  "answer": "신용대출 금리 안내입니다...",
  "intent": {
    "intent": "INQUIRY",
    "keywords": ["신용대출", "금리"]
  },
  "memory_turns": 1,
  "trace_count": 6,
  "evidence_count": 1,
  "decision_v2": {},
  "needs_clarification": false,
  "clarification_question": null
}
```

---

## 21. Related Read APIs

Trace / Evidence:

- `GET /api/v1/ai/traces`
- `GET /api/v1/ai/traces/{request_id}`
- `GET /api/v1/ai/traces/{request_id}/events`
- `GET /api/v1/ai/traces/{request_id}/evidence`

Decision:

- `GET /api/v1/ai/decisions`
- `GET /api/v1/ai/decisions/{request_id}/trace`
- `GET /api/v1/ai/decisions/{request_id}/graph`

운영 화면과 프론트는 위 API를 이용해 request별 파이프라인과 의사결정 정보를 보여준다.

---

## 22. 현재 문서 기준 주의사항

1. 현재 구현은 초기 대출 전용 흐름보다 넓다. `forex`, `notification`도 같은 채팅 파이프라인을 탄다.
2. clarification이 걸리면 Sub-Agent 실행 전에 응답이 끝날 수 있다.
3. 메모리 저장은 수행되지만, 저장 성공 여부가 현재 trace event로 항상 직접 기록되지는 않는다.
4. `results`는 raw Tool 결과가 아니라 rerank 이후 응답용 결과 목록이다.
5. `decision_v2`는 채팅 응답에 직접 포함되며, 별도 decision trace API와는 용도가 다르다.
