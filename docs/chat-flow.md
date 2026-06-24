# Chat Flow

채팅 화면에서 사용자가 질문을 보낸 뒤, Leader Agent가 어떤 순서로 메모리, 의도, Concept, Agent, Tool, Evidence, 최종 답변을 처리하는지 설명한다.

---

## 전체 흐름

```text
User Input
  -> POST /api/v1/ai/chat
  -> AI Gateway
  -> Leader Agent
     1. Short Memory Load
     2. Long-term Memory Load
     3. Intent Analysis
     4. Concept Detection + Expansion
     5. Agent Routing
     6. Sub-Agent / Tool Execution
     7. Re-ranking
     8. Final Answer Generation
     9. Evidence Linking
    10. LeaderDecision / DecisionTrace Save
    11. Long-term Summary Build
    12. Short Memory Save
    13. Long-term Memory Save
    14. Decision Graph Build
  -> ChatResponse
```

---

## 1. Chat UI

- Frontend: `http://localhost:13000/ai/chat`
- Backend Swagger: `http://localhost:18000/docs`
- 요청 예시:

```json
{
  "message": "신용대출 금리와 필요서류 알려줘",
  "session_id": "user-001",
  "channel": "web",
  "user_id": null
}
```

같은 `session_id`를 쓰면 Short Memory와 Long-term Memory가 이어진다.

---

## 2. AI Gateway

파일: [backend/app/api/routes/ai_gateway.py](../backend/app/api/routes/ai_gateway.py)

- `request_id` 생성
- `REQUEST_RECEIVED` trace 저장
- `LeaderAgent.run()` 호출
- 완료 후 `RESPONSE_COMPLETED` trace 저장

---

## 3. Short Memory Load

파일: [backend/app/agents/memory.py](../backend/app/agents/memory.py)

- Redis key: `session:{session_id}:history`
- 최근 최대 5턴 저장
- 실제 원문 메시지 형태로 로드
- TTL: 1시간

Trace:

- `MEMORY_LOADED`
- `output_data.turns_loaded`

---

## 4. Long-term Memory Load

파일: [backend/app/agents/long_term_memory.py](../backend/app/agents/long_term_memory.py)

- PostgreSQL `long_term_memory` 테이블 조회
- 최근 최대 5턴 로드
- 저장된 `question_summary`, `answer_summary`, `intent`, `keywords`, `concepts`를 사용

Trace:

- `LTM_LOADED`
- `output_data.ltm_turns_loaded`

---

## 5. Intent Analysis

파일: [backend/app/agents/leader.py](../backend/app/agents/leader.py)

- `_analyze_intent()`에서 GPT-4o 사용
- 입력:
  - 현재 질문
  - Short Memory 최근 대화
  - Long-term Memory 패턴 힌트
- 출력:
  - `intent`
  - `keywords`
  - `urgency`

Trace:

- `INTENT_ANALYZED`

Decision Trace:

- `intent_analysis.intent`
- `intent_analysis.confidence`
- `intent_analysis.keywords`
- `intent_analysis.reason`

---

## 6. Concept Detection And Expansion

파일:

- [backend/app/agents/leader.py](../backend/app/agents/leader.py)
- [backend/app/knowledge/concept_service.py](../backend/app/knowledge/concept_service.py)

동작:

1. 질문 본문과 intent keyword를 검색어로 사용
2. `business_concept`에서 direct concept 탐지
3. `business_concept_relation`에서 weight 기준으로 expanded concept 추가

Trace:

- `CONCEPT_DETECTED`
- `detected_concepts`
- `expanded_concepts`
- `total_concepts`

Decision Trace:

- `concepts[].detection_stage`
- `concepts[].confidence`
- `concepts[].reason`

---

## 7. Agent Routing

파일: [backend/app/agents/agent_registry.py](../backend/app/agents/agent_registry.py)

- `agent_concept_mapping` 기반
- LLM이 Agent를 임의 선택하지 않음
- `LEADER_AGENT`는 오케스트레이터이며 Sub Agent 선택 목록에 포함되지 않음

Trace:

- `AGENT_SELECTED`
- `routed_agents`
- `unrouted_concepts`

Decision Trace:

- `agent_selection.selected_agents`
- `agent_selection.rejected_agents`
- `leader_decision.direct_concepts`
- `leader_decision.expanded_concepts`

---

## 8. Sub-Agent And Tool Execution

파일:

- [backend/app/agents/leader.py](../backend/app/agents/leader.py)
- 각 Sub Agent 파일
- Tool Gateway

실행:

- Route 결과에 따라 Sub Agent 실행
- 각 Agent는 Tool Gateway를 통해 Mock API 호출
- 성공 결과는 Evidence로 저장

대표 Tool:

- `MOCK_PRODUCT_LOOKUP`
- `MOCK_RATE_LOOKUP`
- `MOCK_POLICY_LOOKUP`
- `MOCK_DOCUMENT_SEARCH`

Trace:

- `PLAN_CREATED`
- `TOOL_INVOKED`

Decision Trace:

- `tool_executions[].tool_name`
- `tool_executions[].input_summary`
- `tool_executions[].output_summary`
- `tool_executions[].latency_ms`

---

## 9. Re-ranking

파일: [backend/app/agents/leader.py](../backend/app/agents/leader.py)

- 성공 여부
- 데이터 충실도
- intent relevance

를 기준으로 결과를 정렬한다.

Trace:

- `RESULTS_RERANKED`

Decision Trace:

- `reranking.criteria_weights`
- `reranking.candidates`
- `reranking.selected_evidence_ids`
- `reranking.reason`

---

## 10. Final Answer

파일: [backend/app/agents/leader.py](../backend/app/agents/leader.py)

- 입력:
  - intent
  - Short Memory
  - Long-term Memory
  - reranked tool result
- GPT-4o 사용 가능 시 자연어 답변 생성
- 실패 시 fallback 답변 사용

Decision Trace:

- `final_answer.answer`
- `final_answer.answer_summary`
- `final_answer.used_evidence_ids`
- `final_answer.grounding_summary`

---

## 11. Evidence Linking

파일: [backend/app/trace/evidence_service.py](../backend/app/trace/evidence_service.py)

- 같은 `request_id` 기준으로 evidence 간 연관 관계를 연결
- concept relation
- shared product id

등을 기반으로 관련 evidence를 묶는다.

---

## 12. LeaderDecision And DecisionTrace Save

파일:

- [backend/app/agents/leader.py](../backend/app/agents/leader.py)
- [backend/app/services/decision_trace_service.py](../backend/app/services/decision_trace_service.py)

저장 대상:

- `leader_decision`
- `ai_decision_trace`
- `ai_concept_detection`
- `ai_agent_selection`
- `ai_tool_execution`
- `ai_reranking_trace`
- `ai_final_answer_trace`

운영 화면은 이 canonical decision trace를 읽어 Summary / Trace / Evidence 화면을 구성한다.

---

## 13. Long-term Summary Build

파일: [backend/app/agents/leader.py](../backend/app/agents/leader.py)

함수:

- `_summarize_for_long_term()`

동작:

- 현재 질문과 최종 답변을 Long-term Memory 저장용으로 별도 요약
- LLM 사용 가능 시 JSON 형태의 `question_summary`, `answer_summary` 생성
- 실패하거나 비활성화면 fallback으로 공백 정리 후 길이 제한 저장

중요:

- 이전 구현은 사실상 단순 절단에 가까웠음
- 현재는 요약 전용 단계를 분리해 저장 흐름에 포함함

---

## 14. Short Memory Save

파일: [backend/app/agents/memory.py](../backend/app/agents/memory.py)

동작:

- `save_turn(session_id, message, answer)`
- Redis에 user / assistant 메시지 1턴 저장
- 최근 5턴만 유지

Trace:

- `MEMORY_SAVED`
- 저장 결과 payload:
  - `saved`
  - `stored_turns`
  - `preview`

---

## 15. Long-term Memory Save

파일: [backend/app/agents/long_term_memory.py](../backend/app/agents/long_term_memory.py)

동작:

- `save_long_term_memory(...)`
- PostgreSQL `long_term_memory`에 저장
- 저장 필드:
  - `intent`
  - `detected_concepts`
  - `keywords`
  - `question_summary`
  - `answer_summary`
  - `turn_index`

Trace:

- `LTM_SAVED`
- 저장 결과 payload:
  - `saved`
  - `turn_index`
  - `question_summary`
  - `answer_summary`

---

## 16. Decision Graph Build

파일:

- [backend/app/agents/graph_builder.py](../backend/app/agents/graph_builder.py)
- [backend/app/api/routes/decisions.py](../backend/app/api/routes/decisions.py)

기본 노드:

- `USER_QUERY`
- `MEMORY_HINT`
- `INTENT`
- `CONCEPT`
- `LEADER_DECISION`
- `SUB_AGENT`
- `TOOL_CALL`
- `RERANKING_SCORE`
- `FINAL_RESPONSE`

메모리 저장 추적:

- `MEMORY_WRITE`
- edge type: `SAVES_MEMORY`

현재 구조:

- Graph builder가 `MEMORY_WRITE`를 이해함
- `/graph` API는 기존 데이터에 `MEMORY_WRITE`가 없을 경우 trace event 기반 fallback 합성을 수행함
- 이미 `MEMORY_WRITE` 노드가 있으면 fallback을 추가하지 않음

운영자가 그래프에서 확인 가능한 메모리 단계:

1. Short Memory Load
2. Long-term Memory Load
3. Final Response
4. Short Memory Save
5. Long-term Memory Save

---

## 17. ChatResponse

응답 예시:

```json
{
  "request_id": "uuid-xxxx",
  "message": "신용대출 금리와 필요서류 알려줘",
  "plan": {
    "detected_concepts": [
      "CONCEPT_PERSONAL_CREDIT_LOAN",
      "CONCEPT_INTEREST_RATE",
      "CONCEPT_REQUIRED_DOCUMENT"
    ],
    "routed_agents": ["PRODUCT_AGENT", "RATE_AGENT", "SEARCH_AGENT"],
    "steps": []
  },
  "results": [],
  "answer": "현재 신용대출 금리와 필요서류는 ...",
  "intent": {
    "intent": "INQUIRY",
    "keywords": ["신용대출", "금리", "필요서류"],
    "urgency": "medium"
  },
  "memory_turns": 1,
  "trace_count": 0,
  "evidence_count": 0
}
```

---

## 운영 화면과의 연결

### Decision Trace

- `/api/v1/ai/decisions/{request_id}/trace`
- 질문, memory, intent, concept, agent reason, tool, reranking, final grounding 확인

### Decision Graph

- `/api/v1/ai/decisions/{request_id}/graph`
- 파이프라인 시각화
- `MEMORY_WRITE` 노드에서 메모리 저장 결과 확인 가능

### Pipeline Explorer

- `/admin/pipeline`
- 좌측 요청 목록, 우측 실행 흐름 요약

---

## 현재 구현 기준 주의사항

1. `LEADER_AGENT`는 Sub Agent 미선택 목록에 노출하지 않는다.
2. Long-term Memory는 원문 전체가 아니라 저장용 요약을 사용한다.
3. Graph의 메모리 저장 단계는 trace event 기반 fallback이 남아 있어, 구버전 데이터도 화면에서 볼 수 있다.
4. 메모리 저장 실패는 trace에 남지만 채팅 응답 자체를 막지는 않는다.
