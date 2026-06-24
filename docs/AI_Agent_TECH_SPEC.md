# TECH_SPEC.md

# Docker 기반 멀티에이전트 AI 서비스 MVP 기술설계서

작성일: 2026-06-09

---

## 1. 기술설계 개요

본 문서는 Docker Compose 기반으로 구동되는 멀티에이전트 AI 서비스 MVP의 기술 구조를 정의한다.

본 설계는 정식 온톨로지 구축이 아니라, PostgreSQL 기반의 **경량 업무 지식 모델**을 중심으로 한다. 해당 모델은 Leader Agent 라우팅, Tool/API 선택, 권한 확인, Trace/Evidence 저장에 활용된다.

---

## 2. 아키텍처 개요

```text
[Client / Swagger / Admin UI]
        ↓
[FastAPI Backend]
        ↓
[AI Gateway]
        ↓
[Leader Agent / Orchestrator]
        ↓
[Sub Agents]
 ├ Product Agent
 ├ Rate Agent
 ├ Policy Agent
 └ Search/RAG Agent
        ↓
[Tool/API Hub]
        ↓
[Mock API / Document Store / Future Internal API]

공통 저장소:
 ├ PostgreSQL: Metadata, Agent Registry, Trace, Evidence
 ├ Redis: Session, Cache, Queue 준비
 └ Volume: 로그, 문서 Seed 데이터
```

---

## 3. Docker Compose 구성

### 3.1 서비스 목록

| 서비스 | 역할 |
|---|---|
| backend | FastAPI API 서버 |
| postgres | 메인 DB |
| redis | 캐시/세션/큐 준비 |
| pgadmin | 개발용 DB 관리 |
| mock-api | 내부 시스템 Mock API |
| worker | 선택: 비동기 Agent 실행 |
| admin-ui | 선택: 관리자 화면 |

---

### 3.2 docker-compose.yml 예시

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai-agent-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - mock-api
    volumes:
      - ./backend:/app
      - ./data:/data
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15
    container_name: ai-agent-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: ai_agent_db
      POSTGRES_USER: ai_agent
      POSTGRES_PASSWORD: ai_agent_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: ai-agent-redis
    ports:
      - "6379:6379"

  pgadmin:
    image: dpage/pgadmin4
    container_name: ai-agent-pgadmin
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    depends_on:
      - postgres

  mock-api:
    build:
      context: ./mock-api
      dockerfile: Dockerfile
    container_name: ai-agent-mock-api
    ports:
      - "8010:8010"
    volumes:
      - ./mock-api:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8010 --reload

volumes:
  postgres_data:
```

---

## 4. Backend 기술 스택

| 영역 | 기술 |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| DB | PostgreSQL 15 |
| Cache | Redis 7 |
| Validation | Pydantic v2 |
| HTTP Client | httpx |
| Test | pytest |
| Container | Docker / Docker Compose |
| API Docs | OpenAPI / Swagger |
| Logging | structlog 또는 logging JSON |

---

## 5. Backend 디렉터리 구조

```text
backend/
 ├ app/
 │  ├ main.py
 │  ├ core/
 │  │  ├ config.py
 │  │  ├ database.py
 │  │  ├ logging_config.py
 │  │  └ security.py
 │  ├ api/routes/
 │  │  ├ ai_gateway_router.py
 │  │  ├ agent_router.py
 │  │  ├ knowledge_router.py
 │  │  ├ tool_router.py
 │  │  └ trace_router.py
 │  ├ agents/
 │  │  ├ base_agent.py
 │  │  ├ leader_agent.py
 │  │  ├ product_agent.py
 │  │  ├ rate_agent.py
 │  │  ├ policy_agent.py
 │  │  └ search_agent.py
 │  ├ orchestrator/
 │  │  ├ planner.py
 │  │  ├ router.py
 │  │  ├ executor.py
 │  │  ├ aggregator.py
 │  │  └ validator.py
 │  ├ knowledge/
 │  │  ├ concept_service.py
 │  │  ├ relation_service.py
 │  │  ├ mapping_service.py
 │  │  └ metadata_resolver.py
 │  ├ tools/
 │  │  ├ tool_gateway.py
 │  │  ├ tool_resolver.py
 │  │  ├ mock_api_client.py
 │  │  └ response_normalizer.py
 │  ├ trace/
 │  │  ├ trace_service.py
 │  │  ├ evidence_service.py
 │  │  └ audit_service.py
 │  ├ models/
 │  │  ├ knowledge_model.py
 │  │  ├ agent_model.py
 │  │  ├ tool_model.py
 │  │  └ trace_model.py
 │  ├ schemas/
 │  │  ├ ai_gateway_schema.py
 │  │  ├ knowledge_schema.py
 │  │  ├ agent_schema.py
 │  │  ├ tool_schema.py
 │  │  └ trace_schema.py
 │  └ seed/
 │     ├ concepts_seed.py
 │     ├ agents_seed.py
 │     └ tools_seed.py
 ├ alembic/
 ├ tests/
 ├ Dockerfile
 ├ requirements.txt
 └ alembic.ini
```

---

## 6. 핵심 처리 흐름

### 6.1 Chat 요청 흐름

```text
1. POST /api/v1/ai/chat
2. request_id 생성
3. trace_event 생성: REQUEST_RECEIVED
4. Leader Agent 호출
5. Metadata Resolver가 query에서 concept_id 식별
6. Agent Router가 concept_id 기준 Agent 선택
7. Tool Resolver가 concept_id 및 agent_id 기준 Tool/API 선택
8. Sub Agent 실행
9. Tool/API Hub가 Mock API 호출
10. Evidence 저장
11. Leader Agent가 결과 통합
12. trace_event 생성: RESPONSE_COMPLETED
13. 최종 응답 반환
```

---

## 7. 경량 업무 지식 모델 DB 설계

### 7.1 business_concept

```sql
CREATE TABLE business_concept (
    concept_id UUID PRIMARY KEY,
    concept_code VARCHAR(100) UNIQUE NOT NULL,
    concept_name VARCHAR(200) NOT NULL,
    concept_type VARCHAR(50) NOT NULL,
    domain VARCHAR(100),
    definition TEXT,
    owner_department VARCHAR(100),
    sensitivity_level VARCHAR(50),
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

### 7.2 business_term_alias

```sql
CREATE TABLE business_term_alias (
    alias_id UUID PRIMARY KEY,
    concept_id UUID NOT NULL REFERENCES business_concept(concept_id),
    alias_name VARCHAR(200) NOT NULL,
    alias_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.3 business_concept_relation

```sql
CREATE TABLE business_concept_relation (
    relation_id UUID PRIMARY KEY,
    source_concept_id UUID NOT NULL REFERENCES business_concept(concept_id),
    relation_type VARCHAR(100) NOT NULL,
    target_concept_id UUID NOT NULL REFERENCES business_concept(concept_id),
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.4 data_source_catalog

```sql
CREATE TABLE data_source_catalog (
    data_source_id UUID PRIMARY KEY,
    source_name VARCHAR(200) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    system_name VARCHAR(100),
    table_name VARCHAR(200),
    description TEXT,
    owner_department VARCHAR(100),
    sensitivity_level VARCHAR(50),
    access_method VARCHAR(50),
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.5 api_catalog

```sql
CREATE TABLE api_catalog (
    api_id UUID PRIMARY KEY,
    api_code VARCHAR(100) UNIQUE NOT NULL,
    api_name VARCHAR(200) NOT NULL,
    system_name VARCHAR(100),
    endpoint VARCHAR(300),
    method VARCHAR(20),
    description TEXT,
    required_permission VARCHAR(100),
    is_mock BOOLEAN DEFAULT true,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.6 concept_data_mapping

```sql
CREATE TABLE concept_data_mapping (
    mapping_id UUID PRIMARY KEY,
    concept_id UUID NOT NULL REFERENCES business_concept(concept_id),
    data_source_id UUID NOT NULL REFERENCES data_source_catalog(data_source_id),
    mapping_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.7 concept_api_mapping

```sql
CREATE TABLE concept_api_mapping (
    mapping_id UUID PRIMARY KEY,
    concept_id UUID NOT NULL REFERENCES business_concept(concept_id),
    api_id UUID NOT NULL REFERENCES api_catalog(api_id),
    operation_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.8 agent_catalog

```sql
CREATE TABLE agent_catalog (
    agent_id UUID PRIMARY KEY,
    agent_code VARCHAR(100) UNIQUE NOT NULL,
    agent_name VARCHAR(200) NOT NULL,
    agent_type VARCHAR(50),
    role_description TEXT,
    prompt_version VARCHAR(50),
    model_name VARCHAR(100),
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT now()
);
```

### 7.9 agent_concept_mapping

```sql
CREATE TABLE agent_concept_mapping (
    mapping_id UUID PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agent_catalog(agent_id),
    concept_id UUID NOT NULL REFERENCES business_concept(concept_id),
    permission_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

---

## 8. Trace/Evidence 설계

### 8.1 trace_event

```sql
CREATE TABLE trace_event (
    trace_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    session_id UUID,
    user_id VARCHAR(100),
    agent_id UUID REFERENCES agent_catalog(agent_id),
    event_type VARCHAR(100),
    input_summary TEXT,
    output_summary TEXT,
    status VARCHAR(50),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT now()
);
```

### 8.2 evidence_reference

```sql
CREATE TABLE evidence_reference (
    evidence_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    trace_id UUID REFERENCES trace_event(trace_id),
    agent_id UUID REFERENCES agent_catalog(agent_id),
    concept_id UUID REFERENCES business_concept(concept_id),
    source_type VARCHAR(50),
    source_id UUID,
    api_id UUID REFERENCES api_catalog(api_id),
    document_id VARCHAR(200),
    chunk_id VARCHAR(200),
    confidence_score NUMERIC(5, 4),
    used_in_response BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);
```

---

## 9. API 설계

### 9.1 AI Gateway API

```http
POST /api/v1/ai/chat
```

Request:

```json
{
  "session_id": "optional-session-id",
  "user_id": "user-001",
  "message": "개인신용대출 금리와 필요서류 알려줘"
}
```

Response:

```json
{
  "request_id": "uuid",
  "session_id": "uuid",
  "answer": "개인신용대출 금리와 필요서류 안내...",
  "used_agents": ["PRODUCT_AGENT", "RATE_AGENT", "POLICY_AGENT"],
  "detected_concepts": ["CONCEPT_LOAN_PRODUCT", "CONCEPT_INTEREST_RATE"],
  "evidence_count": 3
}
```

### 9.2 Knowledge API

```http
GET /api/v1/knowledge/concepts
GET /api/v1/knowledge/concepts/search?keyword=금리
GET /api/v1/knowledge/concepts/{concept_id}/agents
GET /api/v1/knowledge/concepts/{concept_id}/apis
GET /api/v1/knowledge/concepts/{concept_id}/data-sources
```

### 9.3 Tool API

```http
GET  /api/v1/tools
POST /api/v1/tools/invoke
```

Tool Invoke Request:

```json
{
  "request_id": "uuid",
  "agent_code": "RATE_AGENT",
  "concept_codes": ["CONCEPT_INTEREST_RATE"],
  "tool_code": "MOCK_RATE_LOOKUP",
  "parameters": {
    "product_code": "PERSONAL_CREDIT_LOAN"
  }
}
```

### 9.4 Trace API

```http
GET /api/v1/ai/traces/{request_id}
GET /api/v1/ai/traces/{request_id}/evidence
GET /api/v1/ai/traces/{request_id}/events
```

---

## 10. 핵심 서비스 설계

### 10.1 Metadata Resolver

```python
class MetadataResolver:
    def resolve_concepts(self, query: str) -> list[str]:
        """
        business_concept, business_term_alias를 기준으로
        사용자 질문에서 concept_id를 식별한다.
        """
        pass
```

MVP에서는 키워드/동의어 기반 매칭을 우선한다.

---

### 10.2 Agent Router

```python
class AgentRouter:
    def route(self, concept_ids: list[str]) -> list[str]:
        """
        agent_concept_mapping 기준으로 실행 대상 Agent를 선택한다.
        """
        pass
```

라우팅 원칙:

- concept_id 기반 라우팅 우선
- LLM 임의 판단 금지
- Agent 권한 확인
- 중복 Agent 제거
- 실행 순서 정책 적용

---

### 10.3 Tool/API Hub

```python
class ToolGateway:
    async def invoke_tool(
        self,
        request_id: str,
        agent_id: str,
        concept_ids: list[str],
        tool_code: str,
        parameters: dict
    ) -> dict:
        pass
```

처리 순서:

```text
1. tool_code 조회
2. agent_id 권한 확인
3. concept_id와 api_id 매핑 확인
4. parameter validation
5. Mock API 호출
6. response normalization
7. evidence 저장
8. result 반환
```

---

## 11. Mock API 설계

mock-api 서비스는 내부 시스템 대체용이다.

예시 Endpoint:

```http
GET /mock/products
GET /mock/products/{product_code}
GET /mock/rates?product_code=...
GET /mock/policies?product_code=...
GET /mock/documents/search?q=...
```

---

## 12. Seed 데이터

초기 Seed Concept:

```text
CONCEPT_CUSTOMER
CONCEPT_LOAN_PRODUCT
CONCEPT_PERSONAL_CREDIT_LOAN
CONCEPT_INTEREST_RATE
CONCEPT_PREFERENTIAL_RATE
CONCEPT_REQUIRED_DOCUMENT
CONCEPT_POLICY
CONCEPT_TERMS
CONCEPT_COUNSELING_HISTORY
CONCEPT_APPLICATION_CONDITION
```

초기 Agent:

```text
LEADER_AGENT
PRODUCT_AGENT
RATE_AGENT
POLICY_AGENT
SEARCH_AGENT
```

초기 Tool:

```text
MOCK_PRODUCT_LOOKUP
MOCK_RATE_LOOKUP
MOCK_POLICY_LOOKUP
MOCK_DOCUMENT_SEARCH
```

---

## 13. 개발 제외 항목

다음은 명시적으로 제외한다.

```text
- Neo4j
- Graph DB
- RDF/OWL
- SPARQL
- 자동 온톨로지 생성
- 자동 관계 추론
- 전사 용어 표준화
- 모든 DB 컬럼 매핑
- 실제 코어뱅킹 실거래 API
- Kubernetes 운영 배포
```

---

## 14. 품질 기준

| 항목 | 기준 |
|---|---|
| Chat API 정상 응답 | 95% 이상 |
| concept_id 식별 | Seed 시나리오 기준 90% 이상 |
| Agent 라우팅 | Seed 시나리오 기준 90% 이상 |
| Evidence 저장 | 중요 응답 100% |
| Trace 저장 | 모든 요청 100% |
| Docker 실행 | docker compose up 성공 |
| API 문서 | Swagger에서 테스트 가능 |

---

## 15. 결론

본 기술설계는 Docker Compose 기반 로컬 MVP에 적합하도록 범위를 제한한다. 온톨로지와 Graph DB는 제외하되, PostgreSQL 기반 경량 업무 지식 모델을 통해 Agent 실행, API 통제, 근거 추적, 향후 확장성을 확보한다.
