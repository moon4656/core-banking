# TECH_SPEC_TASK.md

# Docker 기반 멀티에이전트 AI 서비스 MVP 개발 작업지시서

작성일: 2026-06-09

---

## 1. 작업지시서 목적

본 문서는 Docker Compose 기반 멀티에이전트 AI 서비스 MVP 개발을 위한 단계별 작업 지시를 정의한다.

본 개발에서는 정식 온톨로지, Graph DB, RDF/OWL, SPARQL을 구현하지 않는다. 대신 PostgreSQL 기반 경량 업무 지식 모델을 구현하여 Leader Agent 라우팅, Tool/API 선택, Trace/Evidence 저장에 활용한다.

---

## 2. 개발 원칙

```text
1. Docker Compose 기반으로 로컬 실행 가능해야 한다.
2. 온톨로지 구축은 제외한다.
3. Knowledge Metadata Service를 경량 업무 지식 모델로 구현한다.
4. Agent는 API를 직접 호출하지 않고 Tool/API Hub를 통해 호출한다.
5. 모든 요청은 Trace를 남긴다.
6. 중요 응답은 Evidence를 남긴다.
7. LLM이 권한과 API 호출을 임의 판단하지 못하게 한다.
8. Agent 라우팅은 concept_id와 mapping table을 우선한다.
9. Mock API로 먼저 검증하고 실제 API는 후속으로 분리한다.
10. Graph DB, Neo4j, RDF/OWL, SPARQL은 본 단계에서 제외한다.
```

---

## 3. Phase 구성

```text
Phase 0. 프로젝트 기본 구조 및 Docker 구성
Phase 1. DB 모델 및 Alembic 마이그레이션
Phase 2. Seed 데이터 구성
Phase 3. Knowledge Metadata Service 개발
Phase 4. Agent Registry 및 Agent Router 개발
Phase 5. Tool/API Hub 및 Mock API 개발
Phase 6. Leader Agent / Orchestrator 개발
Phase 7. Trace/Evidence 저장 개발
Phase 8. AI Gateway Chat API 개발
Phase 9. 통합 테스트 및 Docker 검증
Phase 10. 문서화 및 후속 확장 정리
```

각 Phase는 독립 검증 후 다음 Phase로 진행한다.

---

## Phase 0. 프로젝트 기본 구조 및 Docker 구성

### 목표

Docker Compose 기반 개발 환경을 구성한다.

### 작업

- 프로젝트 루트 생성
- backend 디렉터리 생성
- mock-api 디렉터리 생성
- docker-compose.yml 작성
- backend Dockerfile 작성
- mock-api Dockerfile 작성
- .env.example 작성
- PostgreSQL, Redis, pgAdmin 서비스 구성
- FastAPI 기본 서버 실행 확인

### 산출물

```text
docker-compose.yml
.env.example
backend/Dockerfile
backend/app/main.py
mock-api/Dockerfile
mock-api/main.py
```

### 완료 조건

```text
docker compose up -d --build
curl http://localhost:8000/health
curl http://localhost:8010/health
```

두 API가 정상 응답해야 한다.

---

## Phase 1. DB 모델 및 Alembic 마이그레이션

### 목표

경량 업무 지식 모델과 Trace/Evidence 저장을 위한 DB 스키마를 만든다.

### 작업

다음 테이블 모델을 구현한다.

```text
business_concept
business_term_alias
business_concept_relation
data_source_catalog
api_catalog
concept_data_mapping
concept_api_mapping
agent_catalog
agent_concept_mapping
trace_event
evidence_reference
```

### 파일

```text
backend/app/models/knowledge_model.py
backend/app/models/agent_model.py
backend/app/models/tool_model.py
backend/app/models/trace_model.py
backend/app/core/database.py
alembic/env.py
alembic/versions/*.py
```

### 완료 조건

```bash
docker compose exec backend alembic upgrade head
```

PostgreSQL에 전체 테이블이 생성되어야 한다.

---

## Phase 2. Seed 데이터 구성

### 목표

MVP 테스트용 업무 개념, Agent, Tool, Mapping 데이터를 등록한다.

### Seed 대상 Concept

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

### Seed 대상 Agent

```text
LEADER_AGENT
PRODUCT_AGENT
RATE_AGENT
POLICY_AGENT
SEARCH_AGENT
```

### Seed 대상 Tool/API

```text
MOCK_PRODUCT_LOOKUP
MOCK_RATE_LOOKUP
MOCK_POLICY_LOOKUP
MOCK_DOCUMENT_SEARCH
```

### 작업

- concepts_seed.py 작성
- agents_seed.py 작성
- tools_seed.py 작성
- mappings_seed.py 작성
- Seed 실행 CLI 또는 API 작성

### 완료 조건

다음 명령으로 Seed 데이터가 조회되어야 한다.

```bash
docker compose exec backend python -m app.seed.run_seed
```

---

## Phase 3. Knowledge Metadata Service 개발

### 목표

업무 개념, 동의어, 관계, 매핑 정보를 조회하는 서비스를 개발한다.

### 작업

- Concept CRUD 또는 Read API 구현
- keyword 기반 concept search 구현
- alias 기반 concept search 구현
- concept_id 기준 agents 조회
- concept_id 기준 apis 조회
- concept_id 기준 data sources 조회

### API

```http
GET /api/v1/knowledge/concepts
GET /api/v1/knowledge/concepts/search?keyword=금리
GET /api/v1/knowledge/concepts/{concept_id}/agents
GET /api/v1/knowledge/concepts/{concept_id}/apis
GET /api/v1/knowledge/concepts/{concept_id}/data-sources
```

### 파일

```text
backend/app/api/routes/knowledge_router.py
backend/app/knowledge/concept_service.py
backend/app/knowledge/relation_service.py
backend/app/knowledge/mapping_service.py
backend/app/knowledge/metadata_resolver.py
backend/app/schemas/knowledge_schema.py
```

### 완료 조건

“금리”, “대출”, “필요서류” 키워드로 concept 검색이 가능해야 한다.

---

## Phase 4. Agent Registry 및 Agent Router 개발

### 목표

concept_id 기준으로 실행 대상 Agent를 결정한다.

### 작업

- Agent Catalog 조회 기능 구현
- Agent-Concept Mapping 조회 기능 구현
- AgentRouter 구현
- 중복 Agent 제거
- 기본 실행 순서 정책 구현

### 라우팅 예시

입력:

```json
{
  "concept_codes": [
    "CONCEPT_PERSONAL_CREDIT_LOAN",
    "CONCEPT_INTEREST_RATE",
    "CONCEPT_REQUIRED_DOCUMENT"
  ]
}
```

출력:

```json
{
  "selected_agents": [
    "PRODUCT_AGENT",
    "RATE_AGENT",
    "POLICY_AGENT"
  ]
}
```

### 파일

```text
backend/app/api/routes/agent_router.py
backend/app/orchestrator/router.py
backend/app/agents/base_agent.py
backend/app/schemas/agent_schema.py
```

### 완료 조건

concept_id 또는 concept_code 기준으로 Agent 목록이 반환되어야 한다.

---

## Phase 5. Tool/API Hub 및 Mock API 개발

### 목표

Agent가 직접 API를 호출하지 않고 Tool/API Hub를 통해 Mock API를 호출하도록 한다.

### 작업

- mock-api 서비스 구현
- Tool Gateway 구현
- Tool Resolver 구현
- api_catalog 기반 Tool 조회
- concept_api_mapping 기반 Tool 선택
- Agent 권한 검증
- Mock API 호출
- 응답 정규화

### Mock API Endpoint

```http
GET /mock/products
GET /mock/products/{product_code}
GET /mock/rates?product_code=...
GET /mock/policies?product_code=...
GET /mock/documents/search?q=...
```

### Backend Tool API

```http
GET  /api/v1/tools
POST /api/v1/tools/invoke
```

### 파일

```text
backend/app/api/routes/tool_router.py
backend/app/tools/tool_gateway.py
backend/app/tools/tool_resolver.py
backend/app/tools/mock_api_client.py
backend/app/tools/response_normalizer.py
mock-api/main.py
```

### 완료 조건

Tool Gateway를 통해 Mock 상품/금리/규정 데이터가 조회되어야 한다.

---

## Phase 6. Leader Agent / Orchestrator 개발

### 목표

사용자 질문을 분석하여 concept 식별, Agent 선택, Tool 실행 계획을 생성한다.

### 작업

- Leader Agent 클래스 구현
- Planner 구현
- Metadata Resolver 연동
- Agent Router 연동
- Tool Resolver 연동
- 실행 계획 JSON 생성
- Sub Agent 실행 호출
- 결과 Aggregation 구현

### 실행 계획 예시

```json
{
  "request_id": "REQ-001",
  "detected_concepts": [
    "CONCEPT_PERSONAL_CREDIT_LOAN",
    "CONCEPT_INTEREST_RATE",
    "CONCEPT_REQUIRED_DOCUMENT"
  ],
  "selected_agents": [
    "PRODUCT_AGENT",
    "RATE_AGENT",
    "POLICY_AGENT"
  ],
  "execution_order": [
    "PRODUCT_AGENT",
    "RATE_AGENT",
    "POLICY_AGENT"
  ],
  "tools": [
    "MOCK_PRODUCT_LOOKUP",
    "MOCK_RATE_LOOKUP",
    "MOCK_POLICY_LOOKUP"
  ]
}
```

### 파일

```text
backend/app/agents/leader_agent.py
backend/app/orchestrator/planner.py
backend/app/orchestrator/executor.py
backend/app/orchestrator/aggregator.py
backend/app/orchestrator/validator.py
```

### 완료 조건

사용자 질문 “개인신용대출 금리와 필요서류 알려줘”에 대해 실행 계획이 생성되어야 한다.

---

## Phase 7. Trace/Evidence 저장 개발

### 목표

모든 요청, Agent 실행, Tool 호출, 근거 데이터를 저장한다.

### 작업

- TraceService 구현
- EvidenceService 구현
- REQUEST_RECEIVED 이벤트 저장
- CONCEPT_DETECTED 이벤트 저장
- AGENT_SELECTED 이벤트 저장
- TOOL_INVOKED 이벤트 저장
- RESPONSE_COMPLETED 이벤트 저장
- Evidence 저장
- Trace 조회 API 구현

### API

```http
GET /api/v1/ai/traces/{request_id}
GET /api/v1/ai/traces/{request_id}/events
GET /api/v1/ai/traces/{request_id}/evidence
```

### 파일

```text
backend/app/api/routes/trace_router.py
backend/app/trace/trace_service.py
backend/app/trace/evidence_service.py
backend/app/trace/audit_service.py
backend/app/schemas/trace_schema.py
```

### 완료 조건

Chat 요청 1건당 다음이 저장되어야 한다.

```text
trace_event 3건 이상
evidence_reference 1건 이상
```

---

## Phase 8. AI Gateway Chat API 개발

### 목표

사용자가 질문을 입력하면 최종 응답을 반환하는 Chat API를 완성한다.

### 작업

- POST /api/v1/ai/chat 구현
- request_id 생성
- session_id 생성 또는 재사용
- Leader Agent 호출
- 최종 응답 구성
- used_agents 반환
- detected_concepts 반환
- evidence_count 반환

### Request

```json
{
  "session_id": null,
  "user_id": "user-001",
  "message": "개인신용대출 금리와 필요서류 알려줘"
}
```

### Response

```json
{
  "request_id": "uuid",
  "session_id": "uuid",
  "answer": "개인신용대출 금리와 필요서류 안내...",
  "used_agents": ["PRODUCT_AGENT", "RATE_AGENT", "POLICY_AGENT"],
  "detected_concepts": [
    "CONCEPT_PERSONAL_CREDIT_LOAN",
    "CONCEPT_INTEREST_RATE",
    "CONCEPT_REQUIRED_DOCUMENT"
  ],
  "evidence_count": 3
}
```

### 파일

```text
backend/app/api/routes/ai_gateway_router.py
backend/app/schemas/ai_gateway_schema.py
backend/app/main.py
```

### 완료 조건

Swagger 또는 curl로 Chat API를 호출했을 때 정상 응답해야 한다.

---

## Phase 9. 통합 테스트 및 Docker 검증

### 목표

Docker Compose 환경에서 전체 기능을 검증한다.

### 테스트 항목

```text
1. Docker Compose 전체 실행
2. PostgreSQL 연결
3. Redis 연결
4. Seed 데이터 등록
5. Knowledge API 조회
6. Agent Router 동작
7. Tool Gateway Mock API 호출
8. Leader Agent 실행 계획 생성
9. Chat API 응답
10. Trace/Event 저장
11. Evidence 저장
12. Trace 조회 API 정상 동작
```

### 테스트 파일

```text
backend/tests/test_knowledge_api.py
backend/tests/test_agent_router.py
backend/tests/test_tool_gateway.py
backend/tests/test_leader_agent.py
backend/tests/test_chat_api.py
backend/tests/test_trace_evidence.py
```

### 완료 조건

```bash
docker compose exec backend pytest
```

전체 테스트가 통과해야 한다.

---

## Phase 10. 문서화 및 후속 확장 정리

### 목표

개발 결과와 후속 확장 방향을 정리한다.

### 작업

- README.md 작성
- Docker 실행 가이드 작성
- API 사용 예시 작성
- Seed 데이터 설명 작성
- 설계 제외 범위 명시
- 후속 온톨로지/Graph RAG 확장 로드맵 작성

### 산출물

```text
README.md
DOCKER_RUN_GUIDE.md
API_USAGE_GUIDE.md
SEED_DATA_GUIDE.md
FUTURE_ONTOLOGY_EXTENSION_ROADMAP.md
```

---

## 4. 개발 금지 범위

아래 항목은 본 MVP 개발에서 수행하지 않는다.

```text
1. Neo4j 구축
2. Graph DB 운영
3. RDF/OWL 모델링
4. SPARQL 질의 개발
5. 자동 온톨로지 생성
6. 자동 관계 추론
7. 전사 용어 표준화
8. 모든 DB 컬럼 매핑
9. 실제 코어뱅킹 실거래 API 연계
10. Kubernetes 배포
11. 운영용 보안 인증 체계 완성
12. 장기 메모리 기반 개인정보 저장
```

---

## 5. 우선순위

| 우선순위 | 작업 |
|---|---|
| 1 | Docker Compose 실행 환경 |
| 2 | DB 스키마/Alembic |
| 3 | Seed 데이터 |
| 4 | Knowledge Metadata Service |
| 5 | Agent Router |
| 6 | Tool/API Hub |
| 7 | Leader Agent |
| 8 | Trace/Evidence |
| 9 | Chat API |
| 10 | 테스트/문서 |

---

## 6. 개발 완료 기준

MVP 개발 완료 기준은 다음과 같다.

```text
1. docker compose up -d --build 로 전체 실행 가능
2. Swagger 접속 가능
3. Seed 데이터 등록 가능
4. Chat API 호출 가능
5. Leader Agent가 concept_id를 식별 가능
6. Agent Router가 Agent를 선택 가능
7. Tool/API Hub가 Mock API를 호출 가능
8. 최종 응답 생성 가능
9. Trace/Event 저장 가능
10. Evidence 저장 가능
11. Trace/Evidence 조회 가능
12. 테스트 코드 통과
```

---

## 7. Claude/Codex 개발 지시 시 주의 문구

아래 문구를 반드시 포함한다.

```text
본 단계는 정식 온톨로지 또는 Graph DB 구현 단계가 아니다.

PostgreSQL 기반 경량 업무 지식 모델만 구현한다.
Neo4j, RDF/OWL, SPARQL, Graph RAG는 본 단계에서 제외한다.

Leader Agent는 LLM의 임의 판단이 아니라
business_concept, agent_concept_mapping, concept_api_mapping 기반으로
Agent와 Tool을 선택해야 한다.

모든 Agent 실행과 Tool 호출은 Trace/Event와 Evidence에 저장해야 한다.
```

---

## 8. 최종 결론

본 작업지시서는 Docker 기반 MVP 개발을 위한 현실적인 범위 통제 문서이다. 핵심은 온톨로지를 직접 구현하지 않으면서도, 향후 온톨로지/Graph RAG로 확장 가능한 `concept_id` 중심의 메타데이터 구조를 개발에 반영하는 것이다.
