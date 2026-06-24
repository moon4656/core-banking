# 문서 정합성 검토 결과

작성일: 2026-06-09
검토 대상: AI_Agent_PRD.md, AI_Agent_TECH_SPEC.md, AI_Agent_TECH_SPEC_TASK.md

---

## 1. 전체 판단

**보완 필요**

세 문서의 핵심 설계 방향은 일관되게 정렬되어 있다. 다만 구체적인 구현 단계에서 몇 가지 누락과 불일치가 있어 개발 시작 전 보완이 필요하다. 치명적인 불일치는 없으나 아래 항목을 반영하면 안전하게 Phase 0부터 진행 가능하다.

---

## 2. 문서 간 불일치

| 항목 | 위치 | 문제 | 수정 제안 |
|---|---|---|---|
| Trace 조회 API 경로 | PRD: `GET /api/v1/ai/traces/{request_id}` / TECH_SPEC: `GET /api/v1/ai/traces/{request_id}/events`, `/evidence` 추가 | PRD에는 sub-path가 없고 TECH_SPEC에는 `/events`, `/evidence` 분리 | TECH_SPEC 기준으로 통일 (3개 endpoint) |
| Tool Invoke Request 필드 | TECH_SPEC 9.3 `tool_code` 필드 / TECH_SPEC_TASK Phase 5 `tool_code` 동일 | 일치하지만 `concept_codes` 배열이 PRD에는 명시 없음 | TECH_SPEC 기준 유지, PRD는 추상 수준이므로 무시 |
| Session API | PRD: `GET /api/v1/ai/sessions/{session_id}` | TECH_SPEC, TECH_SPEC_TASK에 해당 endpoint 미포함 | Phase 8 Chat API 개발 시 추가 또는 후속 Phase로 분리 명시 |
| Admin UI | PRD 9절, TECH_SPEC 3.1에 `admin-ui` 선택 서비스로 명시 | TECH_SPEC_TASK에 admin-ui 개발 작업 없음 | MVP 제외로 명시 처리 |
| Worker 서비스 | TECH_SPEC 3.1 `worker` 선택 항목 | TECH_SPEC_TASK에 worker 구현 작업 없음 | MVP 제외로 명시 처리 |
| audit_service | TECH_SPEC 디렉터리 구조에 `audit_service.py` 포함 | TECH_SPEC_TASK Phase 7에 AuditService 언급 없음 | Phase 7에 audit_service 작업 항목 추가 |
| validator.py | TECH_SPEC 디렉터리에 `orchestrator/validator.py` 포함 | TECH_SPEC_TASK Phase 6에 Validator 작업 기술 없음 | Phase 6에 Validator 구현 항목 추가 |

---

## 3. 누락 사항

| 구분 | 누락 내용 | 영향도 | 보완 방법 |
|---|---|---|---|
| Docker | `.env` 파일 docker-compose.yml에서 참조하지만 `.env.example`만 명시 | 중 | `.env` 로컬 생성 가이드를 README 및 Phase 0에 명시 |
| DB | `alembic.ini`의 `sqlalchemy.url` 환경변수 연동 방법 | 중 | `alembic/env.py`에서 `DATABASE_URL` 환경변수 읽도록 명시 |
| API | `GET /api/v1/ai/sessions/{session_id}` endpoint | 하 | Phase 8 또는 후속 Phase로 분리 명시 |
| Seed | `mappings_seed.py` (concept_api_mapping, agent_concept_mapping) | 상 | TECH_SPEC_TASK Phase 2에 있으나 파일명 목록에 누락 — 명시 추가 |
| Test | `conftest.py`, test DB fixture | 중 | Phase 9 테스트 파일 목록에 `conftest.py` 추가 |
| Docker | `postgres` 컨테이너 healthcheck 설정 | 중 | `docker-compose.yml`에 healthcheck 추가 |
| Core | `logging_config.py` 구현 기준 불명확 (structlog vs logging) | 하 | TECH_SPEC에 structlog 우선으로 명시되어 있으므로 structlog 사용 |
| Security | `core/security.py` 역할 불명확 | 하 | MVP에서는 API Key 헤더 검증 수준으로 제한, 내용 명시 |

---

## 4. 과도한 범위

| 항목 | 이유 | 제외 또는 후속 분리 제안 |
|---|---|---|
| `admin-ui` 서비스 | MVP에서 Swagger로 충분히 대체 가능 | Phase 10 이후 별도 태스크로 분리 |
| `worker` 서비스 | Phase 0~9 범위에서 비동기 Agent 실행 필요 없음 | Phase 6 이후 옵션으로 남기고 기본 동기 실행으로 시작 |
| `prometheus` 모니터링 | MVP 성공 기준에 없음 | 제외 |
| `audit_service.py` | `trace_service.py` + `evidence_service.py`로 충분 | 감사 로그 전용 기능은 후속 Phase |
| `core/security.py` 전체 구현 | MVP 운영 보안 인증 제외 원칙 | 파일은 생성하되 내용을 stub(pass-through)으로 제한 |
| Search/RAG Agent 완전 구현 | RAG 파이프라인 전체 구현은 MVP 범위 초과 | Phase 2~3 수준의 Mock 문서 검색으로 제한 |

---

## 5. 반드시 수정해야 할 사항

1. **`mappings_seed.py` 파일명 TECH_SPEC_TASK Phase 2 산출물 목록에 추가** — concept_api_mapping, agent_concept_mapping 없이는 Agent 라우팅이 동작하지 않는다.

2. **`alembic/env.py`에 `DATABASE_URL` 환경변수 연동 명시** — docker 환경에서 hardcode 없이 마이그레이션이 동작해야 한다.

3. **`GET /api/v1/ai/sessions/{session_id}` endpoint MVP 제외 또는 Phase 8 포함 여부 결정 명시** — PRD에는 있으나 TECH_SPEC, TASK에 없어 개발자가 혼동할 수 있다.

4. **`docker-compose.yml`에 postgres healthcheck 추가** — backend가 postgres 준비 전에 기동되면 마이그레이션 실패가 발생한다.

5. **`admin-ui`, `worker`, `prometheus`를 MVP 제외로 docker-compose.yml에 주석 처리** — 선택 서비스임을 명확히 해야 범위 혼동이 없다.

---

## 6. 최종 권고

세 문서는 전반적으로 정합성이 높다. 위 5가지 수정 사항만 반영하면 Phase 0부터 순차 개발이 가능하다.

개발 시작 전 반드시 확인할 사항:

```text
1. .env.example → .env 복사 후 값 설정
2. docker-compose.yml postgres healthcheck 추가
3. mappings_seed.py Phase 2 산출물에 포함
4. admin-ui / worker / prometheus MVP 제외 명시
5. alembic/env.py DATABASE_URL 환경변수 연동
```

전체 설계 방향(concept_id 기반 라우팅, Tool/API Hub 경유, Trace/Evidence 저장, Mock API 우선)은 일관되게 유지되고 있어 MVP 목표 달성에 문제없다.
