# Phase별 승인 프롬프트

작성일: 2026-06-09

각 Phase 시작 전 Claude Code 또는 Codex에 그대로 입력하거나 붙여넣는다.
이전 Phase 완료 및 사용자 승인 없이 다음 Phase를 자동 진행하지 않는다.

---

## Phase 0 승인 프롬프트

```text
Phase 0를 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_PRD.md
2. docs/AI_Agent_TECH_SPEC.md
3. docs/AI_Agent_TECH_SPEC_TASK.md
4. docs/FINAL_PROJECT_STRUCTURE.md
5. CLAUDE.md

수행 범위:
- docker-compose.yml 작성 (backend, postgres, redis, pgadmin, mock-api)
- postgres healthcheck 포함
- .env.example 작성
- backend/Dockerfile, requirements.txt 작성
- backend/app/main.py 작성 (GET /health → {"status": "ok", "service": "backend"})
- backend/app/core/config.py 작성 (Pydantic Settings)
- mock-api/Dockerfile, requirements.txt 작성
- mock-api/main.py 작성 (GET /health → {"status": "ok", "service": "mock-api"})
- README.md 초안 작성

금지 범위:
- DB 모델 구현 금지
- Alembic 구성 금지
- Seed 데이터 금지
- Agent 구현 금지
- Knowledge/Tool/Trace 서비스 구현 금지
- Chat API 구현 금지
- Neo4j/Graph DB/RDF/OWL/SPARQL 금지
- Phase 1 이상 선행 금지

완료 조건:
- curl http://localhost:8000/health → {"status": "ok", "service": "backend"}
- curl http://localhost:8010/health → {"status": "ok", "service": "mock-api"}
- docker compose ps → 전체 서비스 Up 상태
- http://localhost:8000/docs → Swagger UI 접속 가능

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md
- docs/context/CONTEXT_RESTORE.md
- docs/phase/PHASE_0_RESULT.md

완료 후 자동으로 Phase 1을 시작하지 않는다.
완료 조건 달성 후 사용자에게 보고하고 대기한다.
```

---

## Phase 1 승인 프롬프트

```text
Phase 1을 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (7절, 8절 집중)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 1 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/core/database.py 작성 (SQLAlchemy 엔진, 세션, Base)
- backend/app/models/knowledge_model.py (5개 테이블 모델)
- backend/app/models/agent_model.py (2개 테이블 모델)
- backend/app/models/tool_model.py (2개 테이블 모델)
- backend/app/models/trace_model.py (2개 테이블 모델)
- backend/alembic.ini 작성
- backend/alembic/env.py 작성 (DATABASE_URL 환경변수 연동)
- alembic/versions/0001_initial_schema.py 작성 (11개 테이블)
- docker compose exec backend alembic upgrade head 실행

금지 범위:
- Seed 데이터 insert 금지 (테이블 생성만)
- API Router 구현 금지
- Agent/Service 구현 금지
- Graph DB/Neo4j/RDF/OWL/SPARQL 금지
- Phase 2 이상 선행 금지

완료 조건:
- alembic upgrade head 성공
- PostgreSQL에 11개 테이블 생성 확인
- alembic_version 테이블 존재

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_1_RESULT.md

완료 후 자동으로 Phase 2를 시작하지 않는다.
```

---

## Phase 2 승인 프롬프트

```text
Phase 2를 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 2 항목)
2. docs/AI_Agent_TECH_SPEC.md (12절 Seed 데이터)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/seed/concepts_seed.py 작성 (10개 concept)
- backend/app/seed/agents_seed.py 작성 (5개 agent)
- backend/app/seed/tools_seed.py 작성 (4개 tool + api_catalog)
- backend/app/seed/mappings_seed.py 작성 (agent_concept_mapping + concept_api_mapping)
- backend/app/seed/run_seed.py 작성 (중복 실행 방지 포함)
- docker compose exec backend python -m app.seed.run_seed 실행

금지 범위:
- API Router 구현 금지
- Agent 로직 구현 금지
- Phase 3 이상 선행 금지

완료 조건:
- run_seed 실행 후 중복 오류 없이 완료
- business_concept 10행, agent_catalog 5행, api_catalog 4행 이상 확인
- agent_concept_mapping, concept_api_mapping 행 존재

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_2_RESULT.md

완료 후 자동으로 Phase 3을 시작하지 않는다.
```

---

## Phase 3 승인 프롬프트

```text
Phase 3을 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (9.2절 Knowledge API)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 3 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/knowledge/concept_service.py
- backend/app/knowledge/relation_service.py
- backend/app/knowledge/mapping_service.py
- backend/app/knowledge/metadata_resolver.py (keyword/alias 기반 concept_id 식별)
- backend/app/schemas/knowledge_schema.py
- backend/app/api/routes/knowledge_router.py (5개 endpoint)
- main.py에 knowledge_router 등록

API:
- GET /api/v1/knowledge/concepts
- GET /api/v1/knowledge/concepts/search?keyword=금리
- GET /api/v1/knowledge/concepts/{concept_id}/agents
- GET /api/v1/knowledge/concepts/{concept_id}/apis
- GET /api/v1/knowledge/concepts/{concept_id}/data-sources

금지 범위:
- Agent 구현 금지
- Tool/API Hub 구현 금지
- Chat API 구현 금지
- LLM 기반 concept 식별 구현 금지 (keyword/alias 기반만)
- Phase 4 이상 선행 금지

완료 조건:
- "금리", "대출", "필요서류" 키워드로 concept 검색 결과 반환
- metadata_resolver가 질문에서 concept_id 반환

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_3_RESULT.md

완료 후 자동으로 Phase 4를 시작하지 않는다.
```

---

## Phase 4 승인 프롬프트

```text
Phase 4를 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (10.2절 Agent Router)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 4 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/agents/base_agent.py (Agent 추상 클래스)
- backend/app/orchestrator/router.py (concept_id → Agent 선택, agent_concept_mapping 기반)
- backend/app/schemas/agent_schema.py
- backend/app/api/routes/agent_router.py
- main.py에 agent_router 등록

라우팅 원칙:
- concept_id 기반 매핑 테이블 조회 (LLM 임의 판단 금지)
- 중복 Agent 제거
- 실행 순서: PRODUCT → RATE → POLICY → SEARCH

금지 범위:
- Leader Agent 구현 금지
- Tool/API Hub 구현 금지
- Chat API 구현 금지
- Phase 5 이상 선행 금지

완료 조건:
- CONCEPT_INTEREST_RATE → RATE_AGENT 반환
- 복수 concept → 중복 없는 Agent 목록 반환

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_4_RESULT.md

완료 후 자동으로 Phase 5를 시작하지 않는다.
```

---

## Phase 5 승인 프롬프트

```text
Phase 5를 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (10.3절 Tool/API Hub, 11절 Mock API)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 5 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- mock-api/main.py에 Mock API endpoint 5개 추가
- backend/app/tools/mock_api_client.py
- backend/app/tools/tool_resolver.py (concept_api_mapping 기반)
- backend/app/tools/tool_gateway.py (권한 확인 + Tool 호출)
- backend/app/tools/response_normalizer.py
- backend/app/schemas/tool_schema.py
- backend/app/api/routes/tool_router.py
- main.py에 tool_router 등록

Mock API Endpoint:
- GET /mock/products
- GET /mock/products/{product_code}
- GET /mock/rates?product_code=...
- GET /mock/policies?product_code=...
- GET /mock/documents/search?q=...

핵심 원칙:
- Agent는 Tool Gateway를 통해서만 API 호출 (직접 호출 금지)
- Tool 선택은 concept_api_mapping 기반 (LLM 임의 판단 금지)

금지 범위:
- Leader Agent 구현 금지
- Chat API 구현 금지
- 실제 코어뱅킹 API 연계 금지
- Phase 6 이상 선행 금지

완료 조건:
- POST /api/v1/tools/invoke → Mock API 응답 정규화 결과 반환
- Agent 권한 없는 Tool 호출 시 403 반환

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_5_RESULT.md

완료 후 자동으로 Phase 6을 시작하지 않는다.
```

---

## Phase 6 승인 프롬프트

```text
Phase 6을 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (2절 아키텍처, 6절 처리 흐름)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 6 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/orchestrator/planner.py (실행 계획 JSON 생성)
- backend/app/orchestrator/executor.py (Sub Agent 순차 실행)
- backend/app/orchestrator/aggregator.py (결과 통합)
- backend/app/orchestrator/validator.py (응답 안전성 검토)
- backend/app/agents/leader_agent.py (전체 오케스트레이션)
- backend/app/agents/product_agent.py
- backend/app/agents/rate_agent.py
- backend/app/agents/policy_agent.py
- backend/app/agents/search_agent.py

핵심 원칙:
- Leader Agent는 metadata_resolver → agent_router → tool_gateway 순서로 호출
- LLM 임의 판단으로 Agent/Tool 선택 금지
- concept_id 기반 매핑 테이블 우선

금지 범위:
- Trace/Evidence 저장 구현 금지 (Phase 7에서 추가)
- Chat API 완성 금지 (Phase 8에서 완성)
- Phase 7 이상 선행 금지

완료 조건:
- "개인신용대출 금리와 필요서류 알려줘" 입력 시 실행 계획 JSON 생성
- detected_concepts 2개 이상, selected_agents 2개 이상 포함
- 결과 통합 응답 생성

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_6_RESULT.md

완료 후 자동으로 Phase 7을 시작하지 않는다.
```

---

## Phase 7 승인 프롬프트

```text
Phase 7을 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (8절 Trace/Evidence 설계)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 7 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/trace/trace_service.py (trace_event CRUD)
- backend/app/trace/evidence_service.py (evidence_reference CRUD)
- backend/app/trace/audit_service.py (기본 감사 조회)
- backend/app/schemas/trace_schema.py
- backend/app/api/routes/trace_router.py (3개 endpoint)
- Leader Agent에 Trace 저장 연동
- Tool Gateway에 Evidence 저장 연동
- main.py에 trace_router 등록

저장 이벤트:
- REQUEST_RECEIVED
- CONCEPT_DETECTED
- AGENT_SELECTED
- TOOL_INVOKED
- RESPONSE_COMPLETED

Trace API:
- GET /api/v1/ai/traces/{request_id}
- GET /api/v1/ai/traces/{request_id}/events
- GET /api/v1/ai/traces/{request_id}/evidence

금지 범위:
- Chat API 완성 금지 (Phase 8에서)
- Phase 8 이상 선행 금지

완료 조건:
- Chat 요청 1건당 trace_event 3건 이상 저장
- Chat 요청 1건당 evidence_reference 1건 이상 저장
- Trace 조회 API 정상 응답

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_7_RESULT.md

완료 후 자동으로 Phase 8을 시작하지 않는다.
```

---

## Phase 8 승인 프롬프트

```text
Phase 8을 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC.md (9.1절 Chat API)
2. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 8 항목)
3. docs/context/CONTEXT_RESTORE.md
4. CLAUDE.md

수행 범위:
- backend/app/schemas/ai_gateway_schema.py (ChatRequest, ChatResponse)
- backend/app/api/routes/ai_gateway_router.py (POST /api/v1/ai/chat 완성)
- session_id 생성/재사용 로직
- request_id UUID 생성
- used_agents, detected_concepts, evidence_count 응답 구성
- main.py 라우터 최종 확인

Response 형식:
{
  "request_id": "uuid",
  "session_id": "uuid",
  "answer": "...",
  "used_agents": [...],
  "detected_concepts": [...],
  "evidence_count": N
}

금지 범위:
- 실제 코어뱅킹 API 연계 금지
- Kubernetes 관련 금지
- Phase 9 이상 선행 금지

완료 조건:
- POST /api/v1/ai/chat → HTTP 200
- Swagger에서 Chat API 호출 정상 응답
- answer, used_agents, detected_concepts, evidence_count 전체 포함

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_8_RESULT.md

완료 후 자동으로 Phase 9를 시작하지 않는다.
```

---

## Phase 9 승인 프롬프트

```text
Phase 9를 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 9 항목)
2. docs/context/CONTEXT_RESTORE.md
3. CLAUDE.md

수행 범위:
- backend/tests/conftest.py (pytest fixture, 테스트 DB/클라이언트)
- backend/tests/test_knowledge_api.py
- backend/tests/test_agent_router.py
- backend/tests/test_tool_gateway.py
- backend/tests/test_leader_agent.py
- backend/tests/test_chat_api.py
- backend/tests/test_trace_evidence.py
- docker compose exec backend pytest 실행

금지 범위:
- 새로운 기능 추가 금지 (테스트 코드만)
- Phase 10 이상 선행 금지

완료 조건:
- pytest 전체 통과 (0 failed)
- Chat API 시나리오 테스트 1건 이상 포함

Phase 종료 문서 생성:
- docs/context/COMPACT_READY.md (업데이트)
- docs/context/CONTEXT_RESTORE.md (업데이트)
- docs/phase/PHASE_9_RESULT.md

완료 후 자동으로 Phase 10을 시작하지 않는다.
```

---

## Phase 10 승인 프롬프트

```text
Phase 10을 실행한다.

반드시 먼저 읽을 문서:
1. docs/AI_Agent_TECH_SPEC_TASK.md (Phase 10 항목)
2. docs/context/CONTEXT_RESTORE.md
3. CLAUDE.md

수행 범위:
- README.md 최종 완성 (Docker 실행 가이드, API 목록, Swagger URL, pgadmin URL)
- docs/API_USAGE_GUIDE.md 작성
- docs/SEED_DATA_GUIDE.md 작성
- docs/FUTURE_EXTENSION_ROADMAP.md 작성 (온톨로지/Graph RAG 확장 로드맵)

금지 범위:
- 새로운 기능 추가 금지
- 온톨로지/Graph DB 도입 금지
- Kubernetes 운영 배포 관련 내용 금지

완료 조건:
- README 기준으로 신규 개발자가 docker compose up 한 번으로 실행 가능
- Swagger, pgadmin URL, 테스트 방법 모두 README 포함

Phase 종료 문서 생성:
- docs/phase/PHASE_10_RESULT.md
- docs/FINAL_COMPLETION_REPORT.md

MVP 개발 완료.
```
