# 최종 프로젝트 구조

작성일: 2026-06-09

---

## 프로젝트 디렉터리 Tree

```text
c:/temp/core-banking/
├── docker-compose.yml
├── .env.example
├── .env                          (로컬 전용, .gitignore 대상)
├── README.md
├── docs/
│   ├── AI_Agent_PRD.md
│   ├── AI_Agent_TECH_SPEC.md
│   ├── AI_Agent_TECH_SPEC_TASK.md
│   ├── DOC_REVIEW_RESULT.md
│   ├── FINAL_PROJECT_STRUCTURE.md
│   ├── PHASE_DEVELOPMENT_PLAN.md
│   ├── context/
│   │   ├── COMPACT_READY.md      (Phase 종료 시 생성)
│   │   └── CONTEXT_RESTORE.md   (Phase 종료 시 생성)
│   └── phase/
│       ├── PHASE_0_RESULT.md
│       ├── PHASE_1_RESULT.md
│       └── ...
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_knowledge_api.py
│   │   ├── test_agent_router.py
│   │   ├── test_tool_gateway.py
│   │   ├── test_leader_agent.py
│   │   ├── test_chat_api.py
│   │   └── test_trace_evidence.py
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── logging_config.py
│       │   └── security.py
│       ├── api/
│       │   └── routes/
│       │       ├── ai_gateway_router.py
│       │       ├── agent_router.py
│       │       ├── knowledge_router.py
│       │       ├── tool_router.py
│       │       └── trace_router.py
│       ├── agents/
│       │   ├── base_agent.py
│       │   ├── leader_agent.py
│       │   ├── product_agent.py
│       │   ├── rate_agent.py
│       │   ├── policy_agent.py
│       │   └── search_agent.py
│       ├── orchestrator/
│       │   ├── planner.py
│       │   ├── router.py
│       │   ├── executor.py
│       │   ├── aggregator.py
│       │   └── validator.py
│       ├── knowledge/
│       │   ├── concept_service.py
│       │   ├── relation_service.py
│       │   ├── mapping_service.py
│       │   └── metadata_resolver.py
│       ├── tools/
│       │   ├── tool_gateway.py
│       │   ├── tool_resolver.py
│       │   ├── mock_api_client.py
│       │   └── response_normalizer.py
│       ├── trace/
│       │   ├── trace_service.py
│       │   ├── evidence_service.py
│       │   └── audit_service.py
│       ├── models/
│       │   ├── knowledge_model.py
│       │   ├── agent_model.py
│       │   ├── tool_model.py
│       │   └── trace_model.py
│       ├── schemas/
│       │   ├── ai_gateway_schema.py
│       │   ├── knowledge_schema.py
│       │   ├── agent_schema.py
│       │   ├── tool_schema.py
│       │   └── trace_schema.py
│       └── seed/
│           ├── concepts_seed.py
│           ├── agents_seed.py
│           ├── tools_seed.py
│           ├── mappings_seed.py
│           └── run_seed.py
└── mock-api/
    ├── Dockerfile
    ├── requirements.txt
    └── main.py
```

---

## 주요 디렉터리 설명

| 경로 | 역할 |
|---|---|
| `docker-compose.yml` | 전체 서비스 오케스트레이션 (backend, postgres, redis, pgadmin, mock-api) |
| `.env.example` | 환경변수 템플릿. 개발자가 `.env`로 복사 후 값 설정 |
| `backend/app/main.py` | FastAPI 앱 진입점. 라우터 등록, lifespan 이벤트 |
| `backend/app/core/config.py` | Pydantic Settings 기반 환경변수 관리 |
| `backend/app/core/database.py` | SQLAlchemy 엔진, 세션 팩토리, Base 클래스 |
| `backend/app/core/logging_config.py` | structlog 기반 JSON 구조화 로그 설정 |
| `backend/app/core/security.py` | MVP: API Key 헤더 검증 stub |
| `backend/app/api/routes/ai_gateway_router.py` | `POST /api/v1/ai/chat`, Trace 조회 endpoint |
| `backend/app/api/routes/knowledge_router.py` | concept 조회, keyword 검색, concept-agent/api 매핑 조회 |
| `backend/app/api/routes/agent_router.py` | Agent Catalog 조회 endpoint |
| `backend/app/api/routes/tool_router.py` | Tool 목록 조회, Tool 실행 endpoint |
| `backend/app/api/routes/trace_router.py` | Trace/Evidence 조회 endpoint |
| `backend/app/agents/base_agent.py` | Agent 공통 인터페이스 (추상 클래스) |
| `backend/app/agents/leader_agent.py` | 질문 분석, concept 식별 요청, 실행 계획 수립, Sub Agent 결과 통합 |
| `backend/app/agents/product_agent.py` | 상품 정보/조건/필요서류 조회 |
| `backend/app/agents/rate_agent.py` | 금리/우대금리 조회 |
| `backend/app/agents/policy_agent.py` | 규정/약관/제한조건 조회 |
| `backend/app/agents/search_agent.py` | Mock 문서/FAQ 검색 |
| `backend/app/orchestrator/planner.py` | 실행 계획 JSON 생성 |
| `backend/app/orchestrator/router.py` | concept_id → Agent 선택 (agent_concept_mapping 기반) |
| `backend/app/orchestrator/executor.py` | 선택된 Agent 순차 실행 |
| `backend/app/orchestrator/aggregator.py` | 여러 Agent 결과 통합, 최종 응답 구성 |
| `backend/app/orchestrator/validator.py` | 응답 안전성/일관성 검토 |
| `backend/app/knowledge/concept_service.py` | business_concept 조회 |
| `backend/app/knowledge/relation_service.py` | business_concept_relation 조회 |
| `backend/app/knowledge/mapping_service.py` | concept-agent, concept-api, concept-datasource 매핑 조회 |
| `backend/app/knowledge/metadata_resolver.py` | 사용자 query → concept_id 식별 (keyword/alias 기반) |
| `backend/app/tools/tool_gateway.py` | Agent 권한 확인, Tool 호출 진입점 |
| `backend/app/tools/tool_resolver.py` | concept_api_mapping 기반 Tool 선택 |
| `backend/app/tools/mock_api_client.py` | mock-api 서비스 HTTP 호출 |
| `backend/app/tools/response_normalizer.py` | Mock API 응답 → 표준 형식 변환 |
| `backend/app/trace/trace_service.py` | trace_event 생성/조회 |
| `backend/app/trace/evidence_service.py` | evidence_reference 생성/조회 |
| `backend/app/trace/audit_service.py` | Trace/Evidence 기반 감사 조회 (MVP: 기본 수준) |
| `backend/app/models/knowledge_model.py` | business_concept, term_alias, relation, data_source, concept_data_mapping 모델 |
| `backend/app/models/agent_model.py` | agent_catalog, agent_concept_mapping 모델 |
| `backend/app/models/tool_model.py` | api_catalog, concept_api_mapping 모델 |
| `backend/app/models/trace_model.py` | trace_event, evidence_reference 모델 |
| `backend/app/schemas/` | Pydantic v2 Request/Response 스키마 |
| `backend/app/seed/run_seed.py` | Seed 데이터 일괄 등록 진입점 |
| `backend/app/seed/mappings_seed.py` | agent_concept_mapping, concept_api_mapping Seed (핵심) |
| `backend/alembic/` | DB 마이그레이션 관리 |
| `backend/tests/` | pytest 기반 통합/단위 테스트 |
| `mock-api/main.py` | 내부 시스템 대체용 Mock API (FastAPI) |

---

## Docker Compose 서비스 구성

| 서비스 | 포트 | 역할 | MVP 포함 |
|---|---|---|---|
| backend | 8000 | FastAPI API 서버 | 필수 |
| postgres | 5432 | 메타데이터/Trace DB | 필수 |
| redis | 6379 | 캐시/세션/큐 준비 | 필수 |
| pgadmin | 5050 | 개발용 DB 관리 UI | 필수 |
| mock-api | 8010 | 내부 시스템 Mock API | 필수 |
| worker | - | 비동기 Agent 실행 | MVP 제외 |
| admin-ui | - | 관리자 화면 | MVP 제외 |
| prometheus | - | 모니터링 | MVP 제외 |
