# AGENTS.md

## 개요

이 프로젝트는 `LeaderAgent`가 질의를 해석하고, DB 기반 매핑과 내부 정책에 따라 여러 Sub Agent를 조합해 응답을 만드는 계층형 멀티에이전트 시스템이다.

핵심 원칙:

- Agent 선택은 임의 LLM 추론이 아니라 `agent_concept_mapping` 기반 라우팅을 따른다.
- Tool 호출은 직접 URL 접근이 아니라 반드시 `ToolGateway`를 통해 수행한다.
- 모든 요청은 Trace/Event와 Evidence를 남긴다.
- 현재 구현은 초기 대출 MVP를 넘어 `loan`, `forex`, `notification` 도메인까지 확장되어 있다.

---

## 현재 주요 구현 파일

- Leader 오케스트레이션: `backend/app/agents/leader.py`
- Agent 라우팅: `backend/app/agents/agent_registry.py`
- 기본 Agent 인터페이스: `backend/app/agents/base_agent.py`
- Tool Gateway: `backend/app/tools/tool_gateway.py`
- Trace 기록: `backend/app/trace/trace_service.py`
- Evidence 저장/연결: `backend/app/trace/evidence_service.py`
- FastAPI 진입점: `backend/app/main.py`

주의:

- 문서나 과거 메모에 보이는 `backend/app/agents/leader_agent.py`는 현재 기준 파일이 아니다.
- 실제 Leader 구현 파일은 `backend/app/agents/leader.py`다.

---

## Agent 목록

### LEADER_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 전체 요청 오케스트레이션 |
| 구현 파일 | `backend/app/agents/leader.py` |
| agent_type | `leader` |

책임:

- 사용자 메시지와 메모리 문맥을 기반으로 intent 분석
- concept 탐지 및 확장
- concept 기반 Agent 선택
- 실행 step 생성
- Sub Agent 실행
- 결과 재정렬 및 최종 답변 구성
- Validation 적용
- Trace / Evidence / Decision Trace 저장

추가 특징:

- Redis short memory 사용
- DB 기반 long-term memory 사용
- clarification turn 처리 지원
- `decision_v2` 구조 생성

### PRODUCT_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 대출 상품 조회와 상품 추천 |
| 구현 파일 | `backend/app/agents/product_agent.py` |
| agent_type | `product` |
| 대표 Concept | `CONCEPT_LOAN_PRODUCT`, `CONCEPT_PERSONAL_CREDIT_LOAN` |
| 대표 Tool | `MOCK_PRODUCT_LOOKUP` |

### RATE_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 금리 조회, 우대금리, 시뮬레이션, 개인화 금리 |
| 구현 파일 | `backend/app/agents/rate_agent.py` |
| agent_type | `rate` |
| 대표 Concept | `CONCEPT_INTEREST_RATE`, `CONCEPT_PREFERENTIAL_RATE` |
| 대표 Tool | `MOCK_RATE_LOOKUP`, `MOCK_RATE_SIMULATION`, `MOCK_PERSONALIZED_RATE_LOOKUP` |

### POLICY_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 정책, 약관, 신청 조건, 자격 조건 |
| 구현 파일 | `backend/app/agents/policy_agent.py` |
| agent_type | `policy` |
| 대표 Concept | `CONCEPT_POLICY`, `CONCEPT_TERMS`, `CONCEPT_APPLICATION_CONDITION` |
| 대표 Tool | `MOCK_POLICY_LOOKUP`, `MOCK_ELIGIBILITY_CHECK` |

### SEARCH_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 문서 검색, 필요서류, 상담 이력 |
| 구현 파일 | `backend/app/agents/search_agent.py` |
| agent_type | `search` |
| 대표 Concept | `CONCEPT_REQUIRED_DOCUMENT`, `CONCEPT_COUNSELING_HISTORY` |
| 대표 Tool | `MOCK_DOCUMENT_SEARCH`, `MOCK_COUNSELING_HISTORY`, `MOCK_BRANCH_LOOKUP` |

### FOREX_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 환율, 환전 계산, 해외송금, 외화예금 |
| 구현 파일 | `backend/app/agents/forex_agent.py` |
| agent_type | `forex` |
| 대표 Tool | `MOCK_EXCHANGE_RATE_LOOKUP`, `MOCK_CURRENCY_EXCHANGE_CALC`, `MOCK_FOREIGN_REMITTANCE`, `MOCK_FOREIGN_DEPOSIT_RATE` |

### NOTIFICATION_AGENT

| 항목 | 내용 |
|---|---|
| 역할 | 알림 규칙 조회와 Mock 발송 |
| 구현 파일 | `backend/app/agents/notification_agent.py` |
| agent_type | `notification` |
| 대표 Tool | `MOCK_NOTIFICATION_RULES`, `MOCK_NOTIFICATION_SEND` |

---

## Agent 인터페이스

현재 Sub Agent는 `BaseAgent`가 아니라 `AbstractAgent` / `AgentInput` / `AgentOutput` 구조를 사용한다.

```python
# backend/app/agents/base_agent.py
from dataclasses import dataclass, field

@dataclass
class AgentInput:
    message: str
    intent: dict
    concept_ids: list[str]
    api_ids: list[str]
    session_id: str
    request_id: str

@dataclass
class AgentOutput:
    agent_id: str
    api_results: list[dict]
    answer: str = ""
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

class AbstractAgent:
    async def run(self, db, input: AgentInput) -> AgentOutput:
        ...
```

기본 동작:

- `input.api_ids`를 순회하면서 ToolGateway를 호출한다.
- 각 API 결과에 `status`, `data`, `error`, `latency_ms`가 포함된다.
- 성공 비율 기반으로 confidence를 계산한다.

---

## 라우팅 규칙

현재 라우팅은 다음 순서로 이뤄진다.

1. Leader가 intent를 분석한다.
2. Concept resolution service가 직접 탐지와 확장 concept를 만든다.
3. `agent_registry.route_by_concepts()`가 `agent_concept_mapping`을 조회한다.
4. 내부 `RoutingPolicy`가 rule 기반 보정을 적용한다.
5. 실행 순서는 기본 정렬 순서를 따른다.

기본 실행 순서:

1. `PRODUCT_AGENT`
2. `RATE_AGENT`
3. `POLICY_AGENT`
4. `SEARCH_AGENT`
5. `FOREX_AGENT`
6. `NOTIFICATION_AGENT`

보정 규칙:

- 특정 intent synonym 또는 slot 조합이 있으면 특정 Tool이 우선된다.
- `SEARCH_AGENT`는 문서/이력 관련 키워드가 강할 때 보강 선택될 수 있다.
- 실제 선택 결과는 `decision_v2.selected_agents`와 Trace에 남는다.

---

## Tool 목록

현재 seed 기준 Tool은 15개다.

대출 도메인:

- `MOCK_PRODUCT_LOOKUP`
- `MOCK_RATE_LOOKUP`
- `MOCK_POLICY_LOOKUP`
- `MOCK_DOCUMENT_SEARCH`
- `MOCK_RATE_SIMULATION`
- `MOCK_ELIGIBILITY_CHECK`
- `MOCK_COUNSELING_HISTORY`
- `MOCK_BRANCH_LOOKUP`
- `MOCK_PERSONALIZED_RATE_LOOKUP`

외환 도메인:

- `MOCK_EXCHANGE_RATE_LOOKUP`
- `MOCK_CURRENCY_EXCHANGE_CALC`
- `MOCK_FOREIGN_REMITTANCE`
- `MOCK_FOREIGN_DEPOSIT_RATE`

알림 도메인:

- `MOCK_NOTIFICATION_RULES`
- `MOCK_NOTIFICATION_SEND`

원칙:

- Agent는 Tool endpoint를 직접 호출하지 않는다.
- `ToolGateway.invoke_tool()`를 통해 `api_catalog`를 조회하고 호출한다.

---

## Tool 호출 흐름

```text
Sub Agent
  -> ToolGateway.invoke_tool(...)
    1. api_catalog 조회
    2. 요청 파라미터 정규화
    3. Mock API 호출
    4. 응답 정규화
    5. trace_event 기록
    6. evidence_reference 저장 후보 생성
    7. Leader가 evidence 점수화/연결 수행
```

관련 파일:

- `backend/app/tools/tool_gateway.py`
- `backend/app/trace/evidence_service.py`
- `backend/app/trace/evidence_scorer.py`

---

## 실행 흐름

```text
POST /api/v1/ai/chat
  -> REQUEST_RECEIVED 기록
  -> LeaderAgent.run()
  -> short memory / long-term memory 로드
  -> intent 분석
  -> concept 탐지 및 확장
  -> agent 라우팅
  -> execution step 생성
  -> Sub Agent별 Tool 실행
  -> evidence 저장 / 연결
  -> 결과 rerank
  -> answer compose
  -> validation
  -> RESPONSE_COMPLETED 기록
  -> ChatResponse 반환
```

응답에는 다음 정보가 포함될 수 있다.

- `plan`
- `results`
- `answer`
- `intent`
- `memory_turns`
- `trace_count`
- `evidence_count`
- `decision_v2`
- `needs_clarification`

---

## Trace 이벤트

문서상 최소 보장 이벤트:

- `REQUEST_RECEIVED`
- `CONCEPT_DETECTED`
- `AGENT_SELECTED`
- `TOOL_INVOKED`
- `RESPONSE_COMPLETED`

실제 구현에서는 추가 이벤트도 기록된다.

예:

- `MEMORY_LOADED`
- `LTM_LOADED`
- `INTENT_ANALYZED`
- `PLAN_CREATED`

조회 API:

- `GET /api/v1/ai/traces`
- `GET /api/v1/ai/traces/{request_id}`
- `GET /api/v1/ai/traces/{request_id}/events`
- `GET /api/v1/ai/traces/{request_id}/evidence`

---

## 현재 문서화 시 주의사항

- 이 저장소는 더 이상 “대출 3개 Agent만 있는 MVP”가 아니다.
- 문서 수정 시 `leader.py`, `agent_registry.py`, `tools_seed.py`, `agents_seed.py`, `docker-compose.yml`을 우선 기준으로 삼는다.
- 신규 Agent 추가 시 최소한 아래를 함께 갱신해야 한다.

1. `backend/app/agents/<new_agent>.py`
2. `backend/app/agents/leader.py`의 `_AGENT_REGISTRY`
3. `backend/app/seed/agents_seed.py`
4. `backend/app/seed/mappings_seed.py`
5. 필요 시 `backend/app/seed/tools_seed.py`
6. 관련 테스트와 문서
