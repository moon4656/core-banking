# Docker 기반 멀티에이전트 AI 서비스 MVP

PostgreSQL 기반 **경량 업무 지식 모델**을 중심으로 Leader Agent 라우팅, Tool/API Hub, Trace/Evidence 저장을 구현한 MVP.  
사용자의 자연어 질문을 분석해 관련 업무 개념(Concept)을 탐지하고, 전담 Sub-Agent가 Mock API를 호출해 한국어 답변을 생성한다.

---

## 시스템 아키텍처

```
사용자 질문 (자연어)
       │
       ▼
┌─────────────────────────────────────────────────┐
│                 AI Gateway                      │
│   POST /api/v1/ai/chat                         │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│              Planner (Orchestrator)             │
│  1. Keyword → search_concepts() → concept_ids  │
│  2. concept_ids → route_by_concepts() → agents │
│  3. concept → get_apis_by_concept() → steps    │
│  결과: ExecutionPlan (JSON)                     │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│             Executor (Orchestrator)             │
│  ExecutionPlan의 step을 순서대로 실행           │
│  → Tool Hub (invoke_tool) → Mock API 호출       │
│  → TraceEvent 기록 (매 step)                    │
│  → EvidenceReference 기록 (성공 시)             │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│            Aggregator (Orchestrator)            │
│  StepResult 목록 → 한국어 자연어 요약 생성      │
└───────────────┬─────────────────────────────────┘
                │
                ▼
        ChatResponse (JSON)
  (plan / results / answer / trace_count / evidence_count)
```

**핵심 설계 원칙:**
- Agent는 API URL을 직접 알지 않는다 — 반드시 **Tool Hub** 경유
- Agent 라우팅은 DB 테이블(`agent_concept_mapping`) 기반 — LLM 임의 판단 금지
- 모든 요청은 `trace_event`에 저장, 중요 응답은 `evidence_reference`에 저장

---

## 빠른 시작

```bash
# 1. 환경변수 파일 생성
cp .env.example .env

# 2. 전체 서비스 빌드 및 시작 (최초 빌드 2~3분 소요)
docker compose up -d --build

# 3. DB 마이그레이션
docker compose exec backend alembic upgrade head

# 4. Seed 데이터 등록 (Concept, Agent, Tool, Mapping)
docker compose exec backend python -m app.seed.run_seed

# 5. 동작 확인
curl http://localhost:18000/health
# → {"status": "ok", "service": "backend"}
```

---

## 서비스 URL

| 서비스 | 외부 URL | 설명 |
|---|---|---|
| Backend API | http://localhost:18000 | FastAPI 메인 서버 |
| Swagger UI | http://localhost:18000/docs | 브라우저에서 API 직접 테스트 |
| Mock API | http://localhost:18010 | 내부 시스템 Mock (상품/금리/정책/서류) |
| pgAdmin | http://localhost:5050 | DB 관리 UI |

> **pgAdmin 접속 정보:** admin@example.com / admin  
> 서버 추가 시: 호스트 `postgres`, 포트 `5432`, DB `ai_agent_db`, 유저 `ai_agent`

---

## 주요 API 엔드포인트

### Chat API (핵심)

```http
POST /api/v1/ai/chat
Content-Type: application/json

{
  "message": "신용대출 금리 알려줘"
}
```

**응답 예시:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "신용대출 금리 알려줘",
  "plan": {
    "detected_concepts": ["CONCEPT_PERSONAL_CREDIT_LOAN", "CONCEPT_INTEREST_RATE"],
    "routed_agents": ["PRODUCT_AGENT", "RATE_AGENT"],
    "steps": [
      {"step_index": 0, "agent_id": "PRODUCT_AGENT", "api_id": "MOCK_PRODUCT_LOOKUP", "params": {}},
      {"step_index": 1, "agent_id": "RATE_AGENT",    "api_id": "MOCK_RATE_LOOKUP",    "params": {}}
    ]
  },
  "results": [...],
  "answer": "조회 결과: 대출 상품 3건, 금리 3건을(를) 확인했습니다.",
  "trace_count": 5,
  "evidence_count": 2
}
```

### Trace / Evidence 조회

```http
GET /api/v1/ai/traces/{request_id}
GET /api/v1/ai/traces/{request_id}/events
GET /api/v1/ai/traces/{request_id}/evidence
```

### Knowledge

```http
GET  /api/v1/knowledge/concepts                          # 전체 Concept 목록
GET  /api/v1/knowledge/concepts/search?keyword=금리      # 키워드 검색
GET  /api/v1/knowledge/concepts/{concept_id}/agents      # Concept 담당 Agent 조회
GET  /api/v1/knowledge/concepts/{concept_id}/apis        # Concept 연결 API 조회
```

### Tool Hub

```http
GET  /api/v1/tools                         # 등록된 Tool 목록
POST /api/v1/tools/invoke                  # Tool 직접 호출 (테스트용)
```

**Tool 직접 호출 예시:**
```json
{"api_id": "MOCK_PRODUCT_LOOKUP", "params": {}}
{"api_id": "MOCK_RATE_LOOKUP",    "params": {"product_id": "P001"}}
{"api_id": "MOCK_POLICY_LOOKUP",  "params": {}}
{"api_id": "MOCK_DOCUMENT_SEARCH","params": {"keyword": "재직"}}
```

---

## Chat API 처리 흐름 상세

`POST /api/v1/ai/chat` 호출 시 내부에서 일어나는 일:

| 단계 | 모듈 | TraceEvent | 설명 |
|---|---|---|---|
| 1 | ai_gateway.py | `REQUEST_RECEIVED` | 요청 수신, request_id 발급 |
| 2 | planner.py | `CONCEPT_DETECTION` | 메시지 키워드 → BusinessConcept 탐지 |
| 3 | planner.py | `AGENT_ROUTING` | concept_id → agent_concept_mapping 조회 |
| 4 | planner.py | `PLAN_CREATED` | ExecutionPlan (step 목록) 생성 |
| 5 | executor.py | `TOOL_INVOKE` (×N) | 각 step마다 Tool Hub → Mock API 호출 |
| 6 | ai_gateway.py | `RESPONSE_AGGREGATED` | 결과 집계 및 한국어 요약 생성 |

**Concept 탐지 방식:**  
전체 메시지 + 공백 단위 분리 토큰 각각을 `search_concepts()`로 검색.  
`business_concept.concept_name` 또는 `business_term_alias.alias` 와 일치하면 탐지.

---

## 디렉터리 구조

```
core-banking/
├── docker-compose.yml              # 전체 서비스 정의
├── .env.example                    # 환경변수 템플릿
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                    # DB 마이그레이션 스크립트
│   ├── tests/                      # pytest 통합 테스트
│   └── app/
│       ├── main.py                 # FastAPI 앱 진입점, 라우터 등록
│       ├── core/
│       │   ├── config.py           # 환경변수 → Settings (pydantic-settings)
│       │   └── database.py         # SQLAlchemy 엔진 / 세션 / get_db
│       ├── api/routes/
│       │   ├── ai_gateway.py       # POST /api/v1/ai/chat
│       │   ├── knowledge.py        # GET  /api/v1/knowledge/*
│       │   ├── agent.py            # GET  /api/v1/agents/*
│       │   └── tool.py             # GET/POST /api/v1/tools/*
│       ├── agents/
│       │   └── agent_registry.py   # get_all_agents, route_by_concepts
│       ├── orchestrator/
│       │   ├── planner.py          # build_plan: 탐지 → 라우팅 → Step 생성
│       │   ├── executor.py         # execute_plan: Step 순서대로 실행
│       │   └── aggregator.py       # aggregate: StepResult → 한국어 문장
│       ├── knowledge/
│       │   └── concept_service.py  # search_concepts, get_apis_by_concept
│       ├── tools/
│       │   └── tool_gateway.py     # invoke_tool: ApiCatalog 조회 → httpx 호출
│       ├── trace/
│       │   └── trace_service.py    # record_event, record_evidence, Timer
│       ├── models/                 # SQLAlchemy ORM 모델 (DB 테이블 정의)
│       ├── schemas/                # Pydantic 요청/응답 스키마
│       └── seed/                   # 초기 데이터 등록 스크립트
└── mock-api/
    └── main.py                     # 상품/금리/정책/서류 Mock API (포트 8010)
```

---

## DB 테이블 구조

### 경량 업무 지식 모델

| 테이블 | 역할 |
|---|---|
| `business_concept` | 업무 개념 목록 (예: CONCEPT_INTEREST_RATE) |
| `business_term_alias` | 개념의 별칭 (예: "금리" → CONCEPT_INTEREST_RATE) |
| `business_concept_relation` | 개념 간 관계 (부모/자식) |
| `data_source_catalog` | 데이터 소스 카탈로그 |
| `api_catalog` | 호출 가능한 API 목록 (Tool 목록) |
| `concept_data_mapping` | 개념 ↔ 데이터 소스 매핑 |
| `concept_api_mapping` | 개념 ↔ API 매핑 (어떤 개념이 어떤 API를 사용하는지) |
| `agent_catalog` | Agent 목록 (LEADER, PRODUCT, RATE, POLICY, SEARCH) |
| `agent_concept_mapping` | Agent ↔ 개념 매핑 (어떤 개념이 어떤 Agent 담당인지) |

### Trace / Evidence

| 테이블 | 역할 |
|---|---|
| `trace_event` | 요청 처리 단계별 이벤트 기록 (감사 로그) |
| `evidence_reference` | API 호출로 얻은 실제 데이터 근거 저장 |

**Seed 데이터 포함 항목:**
- Concept 10개: CONCEPT_CUSTOMER, CONCEPT_LOAN_PRODUCT, CONCEPT_PERSONAL_CREDIT_LOAN, CONCEPT_INTEREST_RATE, CONCEPT_PREFERENTIAL_RATE, CONCEPT_REQUIRED_DOCUMENT, CONCEPT_POLICY, CONCEPT_TERMS, CONCEPT_COUNSELING_HISTORY, CONCEPT_APPLICATION_CONDITION
- Agent 5개: LEADER_AGENT, PRODUCT_AGENT, RATE_AGENT, POLICY_AGENT, SEARCH_AGENT
- Tool 4개: MOCK_PRODUCT_LOOKUP, MOCK_RATE_LOOKUP, MOCK_POLICY_LOOKUP, MOCK_DOCUMENT_SEARCH

---

## 확장 가이드

### 새 Tool(API) 추가

**예시: 고객 정보 조회 API 추가**

**1단계 — Mock API에 엔드포인트 추가** (`mock-api/main.py`):
```python
@app.get("/customers")
def get_customers():
    return {"customers": [...], "total": 1}
```

**2단계 — Seed 데이터에 Tool 등록** (`backend/app/seed/tools_seed.py`):
```python
ApiCatalog(
    api_id="MOCK_CUSTOMER_LOOKUP",
    name="고객 정보 조회",
    endpoint="/customers",
    method="GET",
    description="Mock 고객 정보 조회",
)
```

**3단계 — Aggregator 레이블 추가** (`backend/app/orchestrator/aggregator.py`):
```python
_API_LABEL = { ..., "MOCK_CUSTOMER_LOOKUP": "고객 정보" }
_COUNT_KEY  = { ..., "MOCK_CUSTOMER_LOOKUP": "customers"  }
```

**4단계 — Concept-API 매핑 추가** (`backend/app/seed/mappings_seed.py`):
```python
ConceptApiMapping(concept_id="CONCEPT_CUSTOMER", api_id="MOCK_CUSTOMER_LOOKUP", priority=1)
```

**5단계 — 컨테이너 재시작 후 Seed 재실행**:
```bash
docker compose restart
docker compose exec backend python -m app.seed.run_seed
```

---

### 새 Agent 추가

코드 변경 없이 DB에 데이터만 추가하면 라우팅이 자동으로 동작한다.

**1단계 — Seed에 Agent 등록** (`backend/app/seed/agents_seed.py`):
```python
AgentCatalog(
    agent_id="CUSTOMER_AGENT",
    name="고객 상담 에이전트",
    agent_type="customer",
    description="고객 정보 조회 전담",
)
```

**2단계 — Agent-Concept 매핑 추가** (`backend/app/seed/mappings_seed.py`):
```python
AgentConceptMapping(agent_id="CUSTOMER_AGENT", concept_id="CONCEPT_CUSTOMER", priority=1)
```

---

## 테스트 실행

```bash
# 전체 테스트 실행
docker compose exec backend pytest -v
```

**테스트 목록 (14개):**

| 파일 | 테스트 | 검증 내용 |
|---|---|---|
| test_health.py | test_health_check | GET /health → status: ok |
| test_knowledge.py | test_search_by_keyword_rate | "금리" → CONCEPT_INTEREST_RATE 탐지 |
| test_knowledge.py | test_search_by_alias | alias 키워드 검색 정상 동작 |
| test_knowledge.py | test_agents_by_concept | CONCEPT_INTEREST_RATE → RATE_AGENT |
| test_knowledge.py | test_apis_by_concept | CONCEPT_INTEREST_RATE → MOCK_RATE_LOOKUP |
| test_agent.py | test_list_agents | 전체 Agent 5개 이상 반환 |
| test_agent.py | test_route_by_concepts | concept_id → Agent 라우팅 정상 |
| test_agent.py | test_route_empty_concepts | 빈 입력 → 빈 라우팅 반환 |
| test_tool.py | test_invoke_valid_tool_mocked | MOCK_PRODUCT_LOOKUP → status: success |
| test_tool.py | test_invoke_invalid_tool | 없는 api_id → status: error |
| test_chat.py | test_chat_concept_detection | Chat → 업무 Concept 탐지 확인 |
| test_chat.py | test_chat_trace_count | trace_count >= 3 |
| test_chat.py | test_chat_evidence_count | evidence_count >= 1 |
| test_chat.py | test_chat_answer_nonempty | answer 비어있지 않음 |

---

## 개발 Phase 완료 현황

| Phase | 내용 | 상태 |
|---|---|---|
| 0 | Docker 기본 구조 | ✅ 완료 |
| 1 | DB 모델 + Alembic | ✅ 완료 |
| 2 | Seed 데이터 | ✅ 완료 |
| 3 | Knowledge Metadata Service | ✅ 완료 |
| 4 | Agent Registry + Router | ✅ 완료 |
| 5 | Tool/API Hub + Mock API | ✅ 완료 |
| 6 | Leader Agent / Orchestrator | ✅ 완료 |
| 7 | Trace/Evidence 저장 | ✅ 완료 |
| 8 | AI Gateway Chat API | ✅ 완료 |
| 9 | 통합 테스트 (pytest 14개) | ✅ 완료 |
| 10 | 문서화 | ✅ 완료 |

---

## 주요 운영 명령

```bash
# 서비스 시작 (빌드 포함)
docker compose up -d --build

# 서비스 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f backend
docker compose logs -f mock-api

# DB 마이그레이션
docker compose exec backend alembic upgrade head

# Seed 데이터 등록
docker compose exec backend python -m app.seed.run_seed

# 테스트 실행
docker compose exec backend pytest -v

# 헬스 체크
curl http://localhost:18000/health
curl http://localhost:18010/health

# 컨테이너 재시작
docker compose restart backend

# 서비스 중지 (데이터 보존)
docker compose down

# 서비스 중지 + 볼륨 삭제 (DB 초기화)
docker compose down -v
```

---

## 환경변수

`.env.example`을 복사해 `.env`로 사용한다. 비밀값은 코드에 하드코딩하지 않는다.

```env
# DB
POSTGRES_DB=ai_agent_db
POSTGRES_USER=ai_agent
POSTGRES_PASSWORD=ai_agent_password
DATABASE_URL=postgresql://ai_agent:ai_agent_password@postgres:5432/ai_agent_db

# Redis
REDIS_URL=redis://redis:6379

# Mock API (컨테이너 내부 통신 주소)
MOCK_API_URL=http://mock-api:8010
```

> `MOCK_API_URL`의 호스트명 `mock-api`는 Docker Compose 서비스명이다.  
> 컨테이너 외부(로컬 PC)에서 직접 접속할 때는 `http://localhost:18010`을 사용한다.

---

## 개발 금지 범위 (MVP 제외)

이 MVP에서 구현하지 않는 항목:

- Neo4j / Graph DB / RDF / OWL / SPARQL
- 자동 온톨로지 생성 / 자동 관계 추론
- 실제 코어뱅킹 실거래 API 연계
- Kubernetes 운영 배포
- 운영용 보안 인증 체계 (JWT 등)
- 장기 메모리 기반 개인정보 저장
