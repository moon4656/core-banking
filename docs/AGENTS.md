# AGENTS.md — Agent 아키텍처 상세 문서

## 전체 구조 개요

```
사용자 메시지
    │
    ▼
POST /api/v1/ai/chat  (ai_gateway.py)
    │
    ▼
LeaderAgent.run()  (leader.py)
    ├─ 1. Short Memory 로드       memory.py → Redis
    ├─ 2. 의도 분석               GPT-4o (없으면 INQUIRY fallback)
    ├─ 3. Concept 탐지 + 확장     concept_service.py → Redis 캐시 → PostgreSQL
    ├─ 4. Agent 라우팅            agent_registry.py → agent_concept_mapping 테이블
    ├─ 5. Sub-Agent 실행          base_agent.py → tool_gateway.py → mock-api
    ├─ 6. Re-ranking              leader._rerank() — 점수 정렬
    ├─ 7. LLM 최종 요약           GPT-4o (없으면 template fallback)
    ├─ 8. Evidence 연결           evidence_service.link_related_evidence()
    ├─ 9. LeaderDecision 기록     leader_decision 테이블
    └─ 10. Short Memory 저장      memory.py → Redis
```

---

## LeaderAgent (leader.py)

### 역할
- 사용자 요청 → 전체 AI 파이프라인 조율
- Sub-Agent를 직접 인스턴스화하고 결과를 통합한다
- LLM 없이도 동작 (OPENAI_API_KEY 없으면 템플릿 모드)

### 의도(Intent) 유형

| 상수 | 값 | 예시 질문 |
|---|---|---|
| `INTENT_INQUIRY` | `"INQUIRY"` | "신용대출 금리가 얼마야?" |
| `INTENT_COMPARISON` | `"COMPARISON"` | "신용대출과 주담대 금리 차이는?" |
| `INTENT_RECOMMENDATION` | `"RECOMMENDATION"` | "나한테 맞는 대출 뭐야?" |
| `INTENT_APPLICATION` | `"APPLICATION"` | "신용대출 어떻게 신청해?" |
| `INTENT_OTHER` | `"OTHER"` | 기타 |

### Sub-Agent 등록 (`_AGENT_REGISTRY`)

```python
_AGENT_REGISTRY: dict[str, type] = {
    "PRODUCT_AGENT": ProductAgent,
    "RATE_AGENT":    RateAgent,
    "POLICY_AGENT":  PolicyAgent,
    "SEARCH_AGENT":  SearchAgent,
}
```

`_AGENT_REGISTRY`에 없는 agent_id(예: `LEADER_AGENT`)가 라우팅되면 `executor.py` fallback 경로로 처리된다.

### Re-ranking 점수 (`_API_INTENT_RELEVANCE`)

`leader._rerank()`는 각 StepResult에 아래 기준으로 점수를 매겨 정렬한다:

- 기본: 성공=1.0, 실패=0.0
- 데이터 충실도: 항목 수 × 0.1 (최대 +0.5)
- 의도 관련도: `_API_INTENT_RELEVANCE` 테이블에서 현재 intent 키워드와 일치하면 +0.5

---

## AbstractAgent (base_agent.py)

### AgentInput 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `message` | `str` | 사용자 원본 질문 |
| `intent` | `dict` | 의도 분석 결과 `{"intent": "INQUIRY", "keywords": [...]}` |
| `concept_ids` | `list[str]` | 이 Agent가 처리할 Concept ID 목록 |
| `api_ids` | `list[str]` | 호출해야 할 Tool ID 목록 |
| `session_id` | `str` | Redis Short Memory 세션 ID |
| `request_id` | `str` | Trace 기록용 요청 ID |

### AgentOutput 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `agent_id` | `str` | 이 결과를 생성한 Agent ID |
| `api_results` | `list[dict]` | `{"api_id", "status", "data", "error", "latency_ms"}` 목록 |
| `answer` | `str` | Sub-Agent 중간 답변 (선택적, Leader가 최종 요약) |
| `confidence` | `float` | 0.0~1.0, 성공 API 수 / 전체 API 수 |
| `metadata` | `dict` | 추가 디버그 정보 |

### 기본 `run()` 동작

```python
async def run(self, db: Session, input: AgentInput) -> AgentOutput:
    for api_id in input.api_ids:
        t = Timer()
        result = await invoke_tool(db, api_id, params={})  # params={} = 전체 조회
        api_results.append({..., "latency_ms": t.elapsed_ms()})
    confidence = success_count / len(api_results)
    return AgentOutput(...)
```

**파라미터 없이(`params={}`) 호출하므로 Mock API의 모든 Query 파라미터는 optional이어야 한다.**

---

## Sub-Agent 상세

### ProductAgent

| 항목 | 내용 |
|---|---|
| `agent_id` | `PRODUCT_AGENT` |
| 담당 Concept | `CONCEPT_LOAN_PRODUCT`, `CONCEPT_PERSONAL_CREDIT_LOAN`, `CONCEPT_CUSTOMER`, `CONCEPT_APPLICATION_CONDITION` |
| 사용 Tool | `MOCK_PRODUCT_LOOKUP`, `MOCK_ELIGIBILITY_CHECK` |
| `run()` | **AbstractAgent 기본 구현 그대로 사용** — 오버라이드 없음 |
| 특이사항 | `MOCK_ELIGIBILITY_CHECK`는 mock-api v0.2.0에서 전체 파라미터 optional화 완료 |

### RateAgent

| 항목 | 내용 |
|---|---|
| `agent_id` | `RATE_AGENT` |
| 담당 Concept | `CONCEPT_INTEREST_RATE`, `CONCEPT_PREFERENTIAL_RATE` |
| 사용 Tool | `MOCK_RATE_LOOKUP`, `MOCK_RATE_SIMULATION` |
| `run()` | `super().run()` 호출 후 `metadata["is_comparison"]` 추가 |
| 특이사항 | `MOCK_RATE_SIMULATION` 기본값: 3천만원 / 36개월 / 5% |

### PolicyAgent

| 항목 | 내용 |
|---|---|
| `agent_id` | `POLICY_AGENT` |
| 담당 Concept | `CONCEPT_POLICY`, `CONCEPT_TERMS` |
| 사용 Tool | `MOCK_POLICY_LOOKUP` |
| `run()` | `super().run()` 호출 후 `metadata["is_application"]` 추가 |
| 특이사항 | 7종 정책(심사기준/우대금리/중도상환/약관/연체정책/한도정책 등) 조회 |

### SearchAgent

| 항목 | 내용 |
|---|---|
| `agent_id` | `SEARCH_AGENT` |
| 담당 Concept | `CONCEPT_REQUIRED_DOCUMENT`, `CONCEPT_COUNSELING_HISTORY` |
| 사용 Tool | `MOCK_DOCUMENT_SEARCH`, `MOCK_COUNSELING_HISTORY` |
| `run()` | **완전 오버라이드** — `MOCK_DOCUMENT_SEARCH`에 `keyword` 파라미터 전달 |
| 특이사항 | 키워드 없으면 전체 서류 반환, `customer_id` 없으면 전체 상담이력 반환 |

---

## Agent 라우팅 (agent_registry.py)

### 동작 원리

```
concept_ids → agent_concept_mapping 테이블 조회 → priority 가장 낮은 Agent 1개 선택
```

- 같은 Agent가 여러 concept을 담당하면 하나의 `AgentRouteItem`으로 통합
- 담당 Agent가 없는 concept은 `unrouted_concept_ids`로 반환

### 온톨로지 확장 (`_expand_via_relations`)

```
CONCEPT_PERSONAL_CREDIT_LOAN (탐지)
    → business_concept_relation (weight >= 0.7)
        → CONCEPT_INTEREST_RATE      (includes, weight=1.0)
        → CONCEPT_PREFERENTIAL_RATE  (includes, weight=0.8)
        → CONCEPT_REQUIRED_DOCUMENT  (requires, weight=0.9)
```

탐지된 concept에서 **weight ≥ 0.7 관계**로 연결된 concept을 자동 추가한다.

---

## Short Memory (memory.py)

```
Redis key : session:{session_id}:history
형식      : [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
최대 보관 : 5턴 (10 메시지)
TTL       : 3600초 (1시간)
```

- `load_history(session_id)` — Redis 장애 시 `[]` 반환 (서비스 중단 없음)
- `save_turn(session_id, user_msg, assistant_msg)` — Redis 장애 시 조용히 무시
- `session_id=None` → 메모리 기능 완전 비활성화 (독립 요청)

---

## Evidence 신뢰도 점수 (evidence_scorer.py)

```
confidence_score = 0.5 × data_quality + 0.4 × intent_relevance + 0.1 × latency_bonus
```

### data_quality_score (0.0~1.0)
- 목록 API: 필수 필드 존재 여부(0.6배) + 항목 수 보너스(최대 0.4) — 필수 수치 null 시 -0.2
- 단건 API: 필수 필드 커버리지(0.6배) + 기본 0.2 — 필수 수치 null 시 -0.2
- 스펙 미정의 API: 기본 0.7

### intent_relevance_score (0.0~1.0)
`_INTENT_RELEVANCE_TABLE`에서 `intent × api_id` 조합으로 조회.

| API | INQUIRY | COMPARISON | APPLICATION |
|---|---|---|---|
| `MOCK_RATE_LOOKUP` | 1.0 | 1.0 | 0.5 |
| `MOCK_DOCUMENT_SEARCH` | 0.5 | 0.3 | **1.0** |
| `MOCK_ELIGIBILITY_CHECK` | 0.4 | 0.4 | **1.0** |
| `MOCK_PRODUCT_LOOKUP` | 0.8 | 0.9 | 0.6 |

### latency_bonus (0.5~1.0)
- ≤ 2,000ms: 1.0
- 2,001~5,000ms: 0.8
- > 5,000ms: 0.5

---

## 새 Sub-Agent 추가 절차

1. **파일 생성**: `backend/app/agents/{name}_agent.py`
   ```python
   from app.agents.base_agent import AbstractAgent, AgentInput, AgentOutput

   class MyAgent(AbstractAgent):
       @property
       def agent_id(self) -> str:
           return "MY_AGENT"

       # 기본 run() 사용 시 이 아래 생략
       # 특수 파라미터 필요 시 super().run() 호출 후 metadata 추가
   ```

2. **`leader.py` 등록**: `_AGENT_REGISTRY`에 추가
   ```python
   _AGENT_REGISTRY["MY_AGENT"] = MyAgent
   ```

3. **DB Seed 등록**:
   - `backend/app/seed/agents_seed.py` — `agent_catalog` 레코드 추가
   - `backend/app/seed/mappings_seed.py` — `agent_concept_mapping` 레코드 추가

4. **Mock API 추가** (필요 시):
   - `mock-api/main.py` — Query 파라미터 전체 optional로 작성
   - `backend/app/seed/tools_seed.py` — `api_catalog` 레코드 추가
   - `backend/app/seed/mappings_seed.py` — `concept_api_mapping` 레코드 추가
   - `backend/app/trace/evidence_scorer.py` — `_REQUIRED_FIELDS`, `_INTENT_RELEVANCE_TABLE` 추가

5. **Seed 재실행**: `docker compose exec backend python -m app.seed.run_seed`

6. **테스트 추가**: `backend/tests/test_chat.py`에 새 의도/시나리오 케이스 추가

---

## Orchestrator 파일 현황

| 파일 | 상태 | 실제 처리 위치 |
|---|---|---|
| `orchestrator/executor.py` | **사용 중** | `leader.py`에서 미등록 Agent fallback 경로로 호출 |
| `orchestrator/planner.py` | **DEPRECATED** | `leader.py` 내부로 통합됨 |
| `orchestrator/aggregator.py` | **DEPRECATED** | `leader._summarize()`로 대체됨 |

---

## TraceEvent 유형 (9종)

| event_type | 기록 시점 | 기록 위치 |
|---|---|---|
| `REQUEST_RECEIVED` | 요청 수신 | `ai_gateway.py` |
| `MEMORY_LOADED` | Short Memory 로드 완료 | `leader.py` |
| `INTENT_ANALYZED` | 의도 분석 완료 | `leader.py` |
| `CONCEPT_DETECTION` | Concept 탐지 + 확장 완료 | `leader.py` |
| `AGENT_ROUTING` | Sub-Agent 라우팅 결정 | `leader.py` |
| `PLAN_CREATED` | 실행 계획 확정 | `leader.py` |
| `TOOL_INVOKE` | Tool(API) 호출 완료 | `executor.py` (fallback 경로) |
| `RESULTS_RERANKED` | Re-ranking 완료 | `leader.py` |
| `RESPONSE_AGGREGATED` | LLM 최종 요약 완료 | `leader.py` |
| `LEADER_COMPLETED` | 전체 파이프라인 완료 | `ai_gateway.py` |
