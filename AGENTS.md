# AGENTS.md

## Agent 구성 개요

이 시스템은 Leader Agent가 Sub Agent를 조율하는 계층형 멀티에이전트 구조를 사용한다.
Agent 선택은 LLM 판단이 아니라 `agent_concept_mapping` 테이블 기반으로 결정된다.

---

## Agent 목록

### LEADER_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 전체 요청 오케스트레이션 |
| 파일 | `backend/app/agents/leader_agent.py` |
| agent_type | `LEADER` |

**책임:**
- 사용자 질문에서 업무 개념(`concept_id`) 식별 — Metadata Resolver 위임
- 실행 계획(Plan) 생성 — Planner 위임
- 실행 대상 Sub Agent 선택 — Agent Router 위임
- Sub Agent 실행 순서 제어 및 병렬/순차 결정 — Executor 위임
- 각 Sub Agent 결과 통합 — Aggregator 위임
- 최종 응답 안전성/일관성 검토 — Validator 위임
- Trace/Evidence 연결

**제약:**
- LLM이 Agent나 Tool을 임의로 선택하지 않는다
- 반드시 `agent_concept_mapping`, `concept_api_mapping` 테이블 기반으로 결정한다

---

### PRODUCT_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 상품 정보, 조건, 필요서류 안내 |
| 파일 | `backend/app/agents/product_agent.py` |
| agent_type | `SUB` |
| 담당 Concept | `CONCEPT_LOAN_PRODUCT`, `CONCEPT_PERSONAL_CREDIT_LOAN`, `CONCEPT_REQUIRED_DOCUMENT` |
| 담당 Tool | `MOCK_PRODUCT_LOOKUP` |

**Mock API 호출 경로:**
```
PRODUCT_AGENT → Tool/API Hub → GET /mock/products/{product_code}
```

---

### RATE_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 금리, 우대금리, 금리 범위 안내 |
| 파일 | `backend/app/agents/rate_agent.py` |
| agent_type | `SUB` |
| 담당 Concept | `CONCEPT_INTEREST_RATE`, `CONCEPT_PREFERENTIAL_RATE` |
| 담당 Tool | `MOCK_RATE_LOOKUP` |

**Mock API 호출 경로:**
```
RATE_AGENT → Tool/API Hub → GET /mock/rates?product_code=...
```

---

### POLICY_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 규정, 약관, 제한조건, 유의사항 안내 |
| 파일 | `backend/app/agents/policy_agent.py` |
| agent_type | `SUB` |
| 담당 Concept | `CONCEPT_POLICY`, `CONCEPT_TERMS`, `CONCEPT_APPLICATION_CONDITION` |
| 담당 Tool | `MOCK_POLICY_LOOKUP` |

**Mock API 호출 경로:**
```
POLICY_AGENT → Tool/API Hub → GET /mock/policies?product_code=...
```

---

### SEARCH_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 문서/FAQ 검색 및 요약 |
| 파일 | `backend/app/agents/search_agent.py` |
| agent_type | `SUB` |
| 담당 Concept | `CONCEPT_COUNSELING_HISTORY` 등 문서 검색 필요 시 |
| 담당 Tool | `MOCK_DOCUMENT_SEARCH` |

**Mock API 호출 경로:**
```
SEARCH_AGENT → Tool/API Hub → GET /mock/documents/search?q=...
```

---

## Orchestrator 컴포넌트

Agent 실행을 지원하는 내부 컴포넌트. Agent가 아니며 독립 실행하지 않는다.

| 컴포넌트 | 파일 | 역할 |
|---|---|---|
| Planner | `orchestrator/planner.py` | concept_id 기반 실행 계획 JSON 생성 |
| AgentRouter | `orchestrator/router.py` | concept_id → Agent 선택 (테이블 기반) |
| Executor | `orchestrator/executor.py` | Sub Agent 실행 순서 제어 |
| Aggregator | `orchestrator/aggregator.py` | 각 Agent 결과 통합 |
| Validator | `orchestrator/validator.py` | 최종 응답 안전성/일관성 검토 |

---

## Tool 목록

Agent는 Tool/API Hub(`ToolGateway`)를 통해서만 외부 API를 호출한다.

| Tool Code | 설명 | Mock 엔드포인트 |
|---|---|---|
| `MOCK_PRODUCT_LOOKUP` | 상품 정보 조회 | `GET /mock/products/{product_code}` |
| `MOCK_RATE_LOOKUP` | 금리 정보 조회 | `GET /mock/rates?product_code=...` |
| `MOCK_POLICY_LOOKUP` | 규정/약관 조회 | `GET /mock/policies?product_code=...` |
| `MOCK_DOCUMENT_SEARCH` | 문서/FAQ 검색 | `GET /mock/documents/search?q=...` |

---

## Agent 라우팅 규칙

```text
1. MetadataResolver가 사용자 질문에서 concept_id 목록을 추출한다.
2. AgentRouter가 agent_concept_mapping 테이블을 조회한다.
3. concept_id에 매핑된 Agent 목록을 반환한다.
4. 중복 Agent를 제거한다.
5. 실행 순서 정책을 적용한다 (기본: PRODUCT → RATE → POLICY → SEARCH).
6. 권한이 없는 Agent는 제외한다.
```

**라우팅 예시:**

입력 concepts:
```json
["CONCEPT_PERSONAL_CREDIT_LOAN", "CONCEPT_INTEREST_RATE", "CONCEPT_REQUIRED_DOCUMENT"]
```

출력 agents:
```json
["PRODUCT_AGENT", "RATE_AGENT", "POLICY_AGENT"]
```

---

## Tool 호출 흐름

```text
Sub Agent
  → ToolGateway.invoke_tool(request_id, agent_id, concept_ids, tool_code, parameters)
    1. tool_code로 api_catalog 조회
    2. agent_id 권한 확인
    3. concept_id와 api_id 매핑 확인
    4. 파라미터 검증
    5. Mock API 호출 (httpx)
    6. 응답 정규화
    7. evidence_reference 저장
    8. 결과 반환
```

---

## Trace 이벤트 타입

Agent 실행 시 다음 이벤트를 `trace_event` 테이블에 저장한다.

| event_type | 저장 시점 |
|---|---|
| `REQUEST_RECEIVED` | Chat API 요청 수신 시 |
| `CONCEPT_DETECTED` | MetadataResolver가 concept 식별 완료 시 |
| `AGENT_SELECTED` | AgentRouter가 Agent 선택 완료 시 |
| `TOOL_INVOKED` | ToolGateway가 Mock API 호출 완료 시 |
| `RESPONSE_COMPLETED` | Leader Agent가 최종 응답 생성 완료 시 |

---

## Agent 클래스 인터페이스

```python
# backend/app/agents/base_agent.py
class BaseAgent:
    agent_code: str
    agent_type: str

    async def execute(
        self,
        request_id: str,
        concept_ids: list[str],
        parameters: dict
    ) -> dict:
        raise NotImplementedError
```

모든 Sub Agent는 `BaseAgent`를 상속하고 `execute`를 구현한다.

---

## Chat 요청 전체 흐름

```text
POST /api/v1/ai/chat
  ↓
AI Gateway (request_id 생성, trace: REQUEST_RECEIVED)
  ↓
Leader Agent
  ↓
MetadataResolver → concept_id 식별 (trace: CONCEPT_DETECTED)
  ↓
AgentRouter → Agent 선택 (trace: AGENT_SELECTED)
  ↓
Planner → 실행 계획 생성
  ↓
Executor → Sub Agent 순차/병렬 실행
  ├ PRODUCT_AGENT → ToolGateway → MOCK_PRODUCT_LOOKUP (trace: TOOL_INVOKED, evidence 저장)
  ├ RATE_AGENT    → ToolGateway → MOCK_RATE_LOOKUP    (trace: TOOL_INVOKED, evidence 저장)
  └ POLICY_AGENT  → ToolGateway → MOCK_POLICY_LOOKUP  (trace: TOOL_INVOKED, evidence 저장)
  ↓
Aggregator → 결과 통합
  ↓
Validator → 안전성 검토
  ↓
최종 응답 반환 (trace: RESPONSE_COMPLETED)
```

---

## MVP 활성화 Agent

초기 MVP에서는 다음 3개 Agent만 활성화해도 된다.

```text
PRODUCT_AGENT
RATE_AGENT
POLICY_AGENT
```

`SEARCH_AGENT`는 구조는 준비하되 선택 활성화한다.
