# Phase 기반 개발 계획

작성일: 2026-06-09

---

## Phase 0. 프로젝트 기본 구조 및 Docker 구성

### 목표
Docker Compose 기반 개발 환경을 구성하고 FastAPI, mock-api 헬스체크 엔드포인트가 정상 응답하는 상태를 만든다.

### 선행 조건
- Docker Desktop 설치 및 실행 중
- Python 3.11 (로컬 빌드 시)
- `.env.example` → `.env` 복사 후 비밀값 확인

### 작업 목록
1. 프로젝트 루트 디렉터리 확인
2. `docker-compose.yml` 작성 (backend, postgres, redis, pgadmin, mock-api)
3. `.env.example` 작성
4. `backend/Dockerfile` 작성
5. `backend/requirements.txt` 작성 (fastapi, uvicorn, sqlalchemy, alembic, pydantic, httpx, redis, structlog, pytest)
6. `backend/app/main.py` 작성 (`/health` endpoint 포함)
7. `backend/app/core/config.py` 작성 (Pydantic Settings)
8. `mock-api/Dockerfile` 작성
9. `mock-api/requirements.txt` 작성
10. `mock-api/main.py` 작성 (`/health` endpoint 포함)
11. `README.md` 초안 작성

### 생성/수정 파일
```text
docker-compose.yml
.env.example
README.md
backend/Dockerfile
backend/requirements.txt
backend/app/__init__.py
backend/app/main.py
backend/app/core/__init__.py
backend/app/core/config.py
mock-api/Dockerfile
mock-api/requirements.txt
mock-api/main.py
```

### 완료 조건
```bash
docker compose up -d --build
curl http://localhost:8000/health  # {"status": "ok"} 반환
curl http://localhost:8010/health  # {"status": "ok"} 반환
```

### 테스트 방법
- Docker Compose 전체 기동 확인
- backend 컨테이너 로그 오류 없음 확인
- mock-api 컨테이너 로그 오류 없음 확인
- pgadmin 접속 확인 (http://localhost:5050)
- Swagger 접속 확인 (http://localhost:8000/docs)

### 승인 기준
- `curl http://localhost:8000/health` → `{"status": "ok"}` 응답
- `curl http://localhost:8010/health` → `{"status": "ok"}` 응답
- `docker compose ps` 전체 서비스 Up 상태

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md
docs/context/CONTEXT_RESTORE.md
docs/phase/PHASE_0_RESULT.md
```

---

## Phase 1. DB 모델 및 Alembic 마이그레이션

### 목표
경량 업무 지식 모델과 Trace/Evidence 테이블을 SQLAlchemy 모델로 작성하고 Alembic으로 PostgreSQL에 적용한다.

### 선행 조건
- Phase 0 완료 (Docker Compose 정상 기동)
- PostgreSQL 컨테이너 헬스체크 통과

### 작업 목록
1. `backend/app/core/database.py` 작성 (SQLAlchemy 엔진, 세션, Base)
2. `backend/app/models/knowledge_model.py` 작성 (5개 테이블)
3. `backend/app/models/agent_model.py` 작성 (2개 테이블)
4. `backend/app/models/tool_model.py` 작성 (2개 테이블)
5. `backend/app/models/trace_model.py` 작성 (2개 테이블)
6. `backend/alembic.ini` 작성
7. `backend/alembic/env.py` 작성 (DATABASE_URL 환경변수 연동)
8. Alembic 초기 마이그레이션 파일 생성

### 생성/수정 파일
```text
backend/app/core/database.py
backend/app/models/__init__.py
backend/app/models/knowledge_model.py
backend/app/models/agent_model.py
backend/app/models/tool_model.py
backend/app/models/trace_model.py
backend/alembic.ini
backend/alembic/env.py
backend/alembic/script.py.mako
backend/alembic/versions/0001_initial_schema.py
```

### DB 모델 기준 (11개 테이블)
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

### 완료 조건
```bash
docker compose exec backend alembic upgrade head
# PostgreSQL에 11개 테이블 생성 확인
```

### 테스트 방법
- pgadmin에서 테이블 목록 확인
- `docker compose exec postgres psql -U ai_agent -d ai_agent_db -c "\dt"` 로 테이블 목록 출력

### 승인 기준
- 11개 테이블 전체 생성 확인
- alembic_version 테이블 존재 확인

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_1_RESULT.md
```

---

## Phase 2. Seed 데이터 구성

### 목표
MVP 테스트용 업무 개념, Agent, Tool, Mapping 데이터를 PostgreSQL에 등록한다.

### 선행 조건
- Phase 1 완료 (11개 테이블 생성)

### 작업 목록
1. `concepts_seed.py` — 10개 업무 개념 등록
2. `agents_seed.py` — 5개 Agent 등록 (LEADER_AGENT 포함)
3. `tools_seed.py` — 4개 Tool/API 등록 + api_catalog 등록
4. `mappings_seed.py` — agent_concept_mapping + concept_api_mapping 등록
5. `run_seed.py` — 전체 Seed 실행 진입점 (중복 실행 방지 포함)

### 생성/수정 파일
```text
backend/app/seed/__init__.py
backend/app/seed/concepts_seed.py
backend/app/seed/agents_seed.py
backend/app/seed/tools_seed.py
backend/app/seed/mappings_seed.py
backend/app/seed/run_seed.py
```

### Seed 데이터 기준
- Concept 10개: CONCEPT_CUSTOMER, CONCEPT_LOAN_PRODUCT, CONCEPT_PERSONAL_CREDIT_LOAN, CONCEPT_INTEREST_RATE, CONCEPT_PREFERENTIAL_RATE, CONCEPT_REQUIRED_DOCUMENT, CONCEPT_POLICY, CONCEPT_TERMS, CONCEPT_COUNSELING_HISTORY, CONCEPT_APPLICATION_CONDITION
- Agent 5개: LEADER_AGENT, PRODUCT_AGENT, RATE_AGENT, POLICY_AGENT, SEARCH_AGENT
- Tool 4개: MOCK_PRODUCT_LOOKUP, MOCK_RATE_LOOKUP, MOCK_POLICY_LOOKUP, MOCK_DOCUMENT_SEARCH

### 완료 조건
```bash
docker compose exec backend python -m app.seed.run_seed
# "Seed 완료" 메시지 출력
```

### 테스트 방법
- pgadmin 또는 psql로 각 테이블 row count 확인
- `SELECT count(*) FROM business_concept;` → 10
- `SELECT count(*) FROM agent_catalog;` → 5

### 승인 기준
- Seed 명령 중복 실행 시 오류 없이 "이미 등록됨" 처리
- business_concept 10행, agent_catalog 5행, api_catalog 4행 이상 확인

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_2_RESULT.md
```

---

## Phase 3. Knowledge Metadata Service 개발

### 목표
업무 개념, 동의어, 관계, 매핑 정보를 조회하는 REST API를 개발한다.

### 선행 조건
- Phase 2 완료 (Seed 데이터 등록)

### 작업 목록
1. `knowledge/concept_service.py` — business_concept 조회, keyword/alias 검색
2. `knowledge/relation_service.py` — concept_relation 조회
3. `knowledge/mapping_service.py` — concept-agent/api/datasource 매핑 조회
4. `knowledge/metadata_resolver.py` — query 문자열 → concept_id 리스트 반환
5. `schemas/knowledge_schema.py` — Pydantic v2 스키마
6. `api/routes/knowledge_router.py` — 5개 endpoint 구현
7. `main.py`에 knowledge_router 등록

### API 목록
```http
GET /api/v1/knowledge/concepts
GET /api/v1/knowledge/concepts/search?keyword=금리
GET /api/v1/knowledge/concepts/{concept_id}/agents
GET /api/v1/knowledge/concepts/{concept_id}/apis
GET /api/v1/knowledge/concepts/{concept_id}/data-sources
```

### 완료 조건
- "금리", "대출", "필요서류" 키워드로 concept 검색 결과 반환
- metadata_resolver가 "개인신용대출 금리" 질문에서 concept_id 2개 이상 반환

### 테스트 방법
- Swagger UI에서 각 endpoint 직접 호출 테스트

### 승인 기준
- 5개 Knowledge API 전체 정상 응답 (200)
- keyword 검색 결과에 alias 포함 (예: "이자"로 검색 시 CONCEPT_INTEREST_RATE 반환)

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_3_RESULT.md
```

---

## Phase 4. Agent Registry 및 Agent Router 개발

### 목표
concept_id 기준으로 실행 대상 Agent를 결정하는 AgentRouter를 구현한다.

### 선행 조건
- Phase 3 완료 (Knowledge Metadata Service 동작)

### 작업 목록
1. `agents/base_agent.py` — Agent 추상 클래스
2. `orchestrator/router.py` — concept_id → Agent 선택 (agent_concept_mapping 기반)
3. `schemas/agent_schema.py` — Agent 스키마
4. `api/routes/agent_router.py` — Agent Catalog 조회 endpoint
5. `main.py`에 agent_router 등록

### 라우팅 원칙
- concept_id 기반 매핑 테이블 조회 (LLM 임의 판단 금지)
- 중복 Agent 제거
- 실행 순서 정책: PRODUCT → RATE → POLICY → SEARCH

### 완료 조건
- concept_codes 입력 시 대응하는 Agent 목록 반환
- 중복 Agent 제거 동작 확인

### 테스트 방법
- `GET /api/v1/knowledge/concepts/{concept_id}/agents` 호출로 확인

### 승인 기준
- CONCEPT_INTEREST_RATE → RATE_AGENT 반환
- CONCEPT_PERSONAL_CREDIT_LOAN + CONCEPT_INTEREST_RATE → [PRODUCT_AGENT, RATE_AGENT] 중복 없이 반환

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_4_RESULT.md
```

---

## Phase 5. Tool/API Hub 및 Mock API 개발

### 목표
Agent가 직접 API를 호출하지 않고 Tool/API Hub를 통해 Mock API를 호출하도록 구현한다.

### 선행 조건
- Phase 4 완료 (Agent Router 동작)

### 작업 목록
1. `mock-api/main.py` — Mock API 5개 endpoint 구현
2. `tools/mock_api_client.py` — mock-api HTTP 호출 클라이언트
3. `tools/tool_resolver.py` — concept_api_mapping 기반 Tool 선택
4. `tools/tool_gateway.py` — 권한 확인 + Tool 호출 진입점
5. `tools/response_normalizer.py` — 응답 정규화
6. `schemas/tool_schema.py` — Tool 스키마
7. `api/routes/tool_router.py` — Tool 목록/실행 endpoint
8. `main.py`에 tool_router 등록

### Mock API Endpoint
```http
GET /mock/products
GET /mock/products/{product_code}
GET /mock/rates?product_code=...
GET /mock/policies?product_code=...
GET /mock/documents/search?q=...
GET /health
```

### 완료 조건
- Tool Gateway를 통해 Mock 상품/금리/규정 데이터 조회 성공
- Agent 권한 없는 Tool 호출 시 403 반환

### 승인 기준
- `POST /api/v1/tools/invoke` 호출 시 Mock API 응답 정규화 결과 반환
- tool_call_log에 호출 이력 저장

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_5_RESULT.md
```

---

## Phase 6. Leader Agent / Orchestrator 개발

### 목표
사용자 질문을 분석하여 concept 식별, Agent 선택, Tool 실행 계획 생성, Sub Agent 실행 및 결과 통합을 수행한다.

### 선행 조건
- Phase 5 완료 (Tool/API Hub 동작)

### 작업 목록
1. `orchestrator/planner.py` — 실행 계획 JSON 생성
2. `orchestrator/executor.py` — Sub Agent 순차 실행
3. `orchestrator/aggregator.py` — 결과 통합
4. `orchestrator/validator.py` — 응답 안전성 검토
5. `agents/leader_agent.py` — 전체 오케스트레이션
6. `agents/product_agent.py`, `rate_agent.py`, `policy_agent.py`, `search_agent.py` — Sub Agent 구현

### 실행 계획 형식
```json
{
  "request_id": "uuid",
  "detected_concepts": ["CONCEPT_PERSONAL_CREDIT_LOAN", "CONCEPT_INTEREST_RATE"],
  "selected_agents": ["PRODUCT_AGENT", "RATE_AGENT"],
  "execution_order": ["PRODUCT_AGENT", "RATE_AGENT"],
  "tools": ["MOCK_PRODUCT_LOOKUP", "MOCK_RATE_LOOKUP"]
}
```

### 완료 조건
- "개인신용대출 금리와 필요서류 알려줘" 입력 시 실행 계획 JSON 생성
- Sub Agent 실행 후 결과 통합 응답 생성

### 승인 기준
- 실행 계획에 detected_concepts 2개 이상, selected_agents 2개 이상 포함
- Aggregator가 각 Agent 결과를 하나의 응답으로 통합

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_6_RESULT.md
```

---

## Phase 7. Trace/Evidence 저장 개발

### 목표
모든 요청, Agent 실행, Tool 호출 이력과 응답 근거를 trace_event, evidence_reference에 저장한다.

### 선행 조건
- Phase 6 완료 (Leader Agent 동작)

### 작업 목록
1. `trace/trace_service.py` — trace_event CRUD
2. `trace/evidence_service.py` — evidence_reference CRUD
3. `trace/audit_service.py` — 감사 조회 기능 (기본 수준)
4. `schemas/trace_schema.py` — Trace/Evidence 스키마
5. `api/routes/trace_router.py` — Trace 조회 3개 endpoint
6. Leader Agent, Tool Gateway에 Trace/Evidence 저장 연동
7. `main.py`에 trace_router 등록

### 저장 이벤트 종류
```text
REQUEST_RECEIVED
CONCEPT_DETECTED
AGENT_SELECTED
TOOL_INVOKED
RESPONSE_COMPLETED
```

### Trace 조회 API
```http
GET /api/v1/ai/traces/{request_id}
GET /api/v1/ai/traces/{request_id}/events
GET /api/v1/ai/traces/{request_id}/evidence
```

### 완료 조건
- Chat 요청 1건당 trace_event 3건 이상 저장
- Chat 요청 1건당 evidence_reference 1건 이상 저장

### 승인 기준
- Trace 조회 API에서 저장된 이벤트 전체 반환
- evidence_reference에 concept_id, api_id, confidence_score 포함

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_7_RESULT.md
```

---

## Phase 8. AI Gateway Chat API 개발

### 목표
사용자 질문 입력 → 최종 응답 반환하는 Chat API를 완성한다.

### 선행 조건
- Phase 7 완료 (Trace/Evidence 저장 동작)

### 작업 목록
1. `schemas/ai_gateway_schema.py` — ChatRequest, ChatResponse 스키마
2. `api/routes/ai_gateway_router.py` — `POST /api/v1/ai/chat` 구현
3. session_id 생성/재사용 로직 구현
4. request_id UUID 생성
5. Leader Agent 호출 연동
6. used_agents, detected_concepts, evidence_count 응답 구성
7. `main.py` 라우터 최종 확인

### Request/Response 형식
```json
Request:
{
  "session_id": null,
  "user_id": "user-001",
  "message": "개인신용대출 금리와 필요서류 알려줘"
}

Response:
{
  "request_id": "uuid",
  "session_id": "uuid",
  "answer": "개인신용대출 금리는 ...",
  "used_agents": ["PRODUCT_AGENT", "RATE_AGENT", "POLICY_AGENT"],
  "detected_concepts": ["CONCEPT_PERSONAL_CREDIT_LOAN", "CONCEPT_INTEREST_RATE"],
  "evidence_count": 3
}
```

### 완료 조건
- Swagger에서 Chat API 호출 시 정상 응답 반환
- used_agents, detected_concepts 포함 확인

### 승인 기준
- `POST /api/v1/ai/chat` → HTTP 200
- response에 answer, used_agents, detected_concepts, evidence_count 전체 포함

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_8_RESULT.md
```

---

## Phase 9. 통합 테스트 및 Docker 검증

### 목표
Docker Compose 환경에서 전체 기능을 pytest로 검증한다.

### 선행 조건
- Phase 8 완료 (Chat API 정상 응답)

### 작업 목록
1. `tests/conftest.py` — pytest fixture (테스트 DB, 클라이언트)
2. `tests/test_knowledge_api.py`
3. `tests/test_agent_router.py`
4. `tests/test_tool_gateway.py`
5. `tests/test_leader_agent.py`
6. `tests/test_chat_api.py`
7. `tests/test_trace_evidence.py`

### 완료 조건
```bash
docker compose exec backend pytest
# 전체 테스트 PASS
```

### 승인 기준
- pytest 전체 통과 (0 failed)
- Chat API 시나리오 테스트 1건 이상 포함

### Phase 종료 시 생성 문서
```text
docs/context/COMPACT_READY.md (업데이트)
docs/context/CONTEXT_RESTORE.md (업데이트)
docs/phase/PHASE_9_RESULT.md
```

---

## Phase 10. 문서화 및 후속 확장 정리

### 목표
개발 결과와 후속 확장 방향을 문서로 정리한다.

### 작업 목록
1. `README.md` 최종 완성 (Docker 실행 가이드 포함)
2. `docs/API_USAGE_GUIDE.md` — API 사용 예시
3. `docs/SEED_DATA_GUIDE.md` — Seed 데이터 설명
4. `docs/FUTURE_EXTENSION_ROADMAP.md` — 온톨로지/Graph RAG 확장 로드맵

### 완료 조건
- README 기준으로 신규 개발자가 docker compose up 한 번으로 전체 실행 가능
- Swagger URL, pgadmin URL, 테스트 방법 모두 README에 포함

### 승인 기준
- README 읽고 별도 안내 없이 실행 가능한 수준

### Phase 종료 시 생성 문서
```text
docs/phase/PHASE_10_RESULT.md
docs/FINAL_COMPLETION_REPORT.md
```
