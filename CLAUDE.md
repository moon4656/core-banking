# CLAUDE.md

## 프로젝트 요약

`core-banking`은 FastAPI 백엔드, Next.js 프론트엔드, PostgreSQL, Redis, Mock API로 구성된 멀티에이전트 금융 상담 데모 시스템이다.

초기에는 대출 상담 MVP 중심이었지만, 현재 코드 기준으로는 다음 도메인을 포함한다.

- 대출 상품 / 금리 / 정책 / 필요서류
- 상담 이력 / 문서 검색
- 외환 조회 / 환전 계산 / 해외송금 / 외화예금
- 알림 규칙 조회 / 알림 발송 Mock
- Trace / Evidence / Decision Trace / 모니터링 / 관리자 화면

---

## 작업 전 빠른 체크

이 저장소에서 작업할 때 우선 확인할 파일:

- 앱 진입점: `backend/app/main.py`
- 채팅 API: `backend/app/api/routes/ai_gateway.py`
- Leader 구현: `backend/app/agents/leader.py`
- Agent 라우팅: `backend/app/agents/agent_registry.py`
- Tool 호출: `backend/app/tools/tool_gateway.py`
- 인증/권한: `backend/app/core/security.py`
- 환경설정: `backend/app/core/config.py`
- Seed: `backend/app/seed/run_seed.py`
- 도커 구성: `docker-compose.yml`

주의:

- 예전 문서에 남아 있는 `leader_agent.py` 경로는 현재 구현과 다르다.
- 실제 Leader는 `backend/app/agents/leader.py`에 있다.

---

## 기술 스택

백엔드:

- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL 15
- Redis 7
- httpx
- OpenAI Python SDK
- pytest

프론트엔드:

- Next.js 15
- React 18
- TypeScript
- MUI
- TanStack Query
- React Flow (`@xyflow/react`)

---

## 서비스 포트

`docker-compose.yml` 기준:

- Frontend: `http://localhost:13000`
- Backend API: `http://localhost:18000`
- Backend Swagger: `http://localhost:18000/docs`
- Mock API: `http://localhost:18010`
- PostgreSQL: `localhost:15433`
- pgAdmin: `http://localhost:15050`
- Redis: `localhost:6379`

---

## 현재 아키텍처 핵심

### Backend

- `/api/v1/ai/chat`가 메인 진입점이다.
- `LeaderAgent`가 intent 분석, concept resolution, agent routing, execution planning, answer composition을 수행한다.
- Agent 선택은 DB 매핑을 기반으로 하고, 추가 정책은 `RoutingPolicy`가 보정한다.
- Tool 호출은 `ToolGateway`만 사용한다.
- 모든 실행은 Trace와 Evidence로 남긴다.

### Frontend

- Next.js App Router 기반이다.
- 사용자 채팅 화면은 `frontend/src/app/ai/chat/page.tsx`
- 관리자/분석 화면은 `frontend/src/app/admin/*`, `frontend/src/app/analysis/*`
- Decision Graph, Trace Viewer, Monitoring UI가 포함돼 있다.

---

## 현재 활성 Agent

- `LEADER_AGENT`
- `PRODUCT_AGENT`
- `RATE_AGENT`
- `POLICY_AGENT`
- `SEARCH_AGENT`
- `FOREX_AGENT`
- `NOTIFICATION_AGENT`

Agent seed 기준 파일:

- `backend/app/seed/agents_seed.py`

---

## 현재 Tool 범위

대표 Tool:

- 대출: `MOCK_PRODUCT_LOOKUP`, `MOCK_RATE_LOOKUP`, `MOCK_POLICY_LOOKUP`
- 검색/서류: `MOCK_DOCUMENT_SEARCH`, `MOCK_COUNSELING_HISTORY`, `MOCK_BRANCH_LOOKUP`
- 금리 계산: `MOCK_RATE_SIMULATION`, `MOCK_PERSONALIZED_RATE_LOOKUP`, `MOCK_ELIGIBILITY_CHECK`
- 외환: `MOCK_EXCHANGE_RATE_LOOKUP`, `MOCK_CURRENCY_EXCHANGE_CALC`, `MOCK_FOREIGN_REMITTANCE`, `MOCK_FOREIGN_DEPOSIT_RATE`
- 알림: `MOCK_NOTIFICATION_RULES`, `MOCK_NOTIFICATION_SEND`

기준 파일:

- `backend/app/seed/tools_seed.py`
- `mock-api/main.py`

---

## 인증/권한

현재 인증은 `X-API-Key` 또는 Bearer 세션 토큰을 사용한다.

권한 계층:

- `READONLY`
- `ANALYST`
- `ADMIN`

중요 사항:

- `AUTH_ENABLED=false`면 내부적으로 `ADMIN`처럼 동작한다.
- `/api/v1/ai/chat`는 `require_analyst_context`를 사용한다.
- Trace 조회는 소유자 스코프가 적용된다. `ADMIN`만 전체 접근 가능하다.

관련 파일:

- `backend/app/core/security.py`
- `backend/app/api/routes/trace.py`
- `backend/app/api/routes/auth.py`

---

## 메모리 구조

Short memory:

- Redis 기반
- 세션별 최근 대화 문맥 저장
- `backend/app/agents/memory.py`

Long-term memory:

- DB 기반
- 과거 상담 요약 저장
- `backend/app/agents/long_term_memory.py`

Clarification:

- 누락 슬롯이 있으면 즉시 실행하지 않고 보충 질문을 반환할 수 있다.

---

## 디렉터리 가이드

```text
backend/app/
  agents/        Leader, Sub Agent, 라우팅/응답 조합 서비스
  api/routes/    FastAPI 라우트
  core/          설정, DB, 보안
  knowledge/     concept 조회/탐지
  models/        SQLAlchemy 모델
  schemas/       Pydantic 스키마
  seed/          초기 데이터 적재
  services/      decision trace, monitoring 등
  tools/         ToolGateway
  trace/         trace / evidence 처리
  static/        백엔드 제공 정적 UI

frontend/src/app/
  ai/chat/       사용자 채팅 UI
  admin/         관리자 기능
  analysis/      trace 분석 화면
  dashboard/     대시보드
  inquiry/       inquiry/concept 화면
```

---

## 자주 쓰는 명령

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed.run_seed
docker compose exec backend pytest
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mock-api
```

헬스 체크:

```bash
curl http://localhost:18000/health
curl http://localhost:18010/health
```

---

## 테스트 힌트

주요 백엔드 테스트 파일:

- `backend/tests/test_chat.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_trace_access_scope.py`
- `backend/tests/test_decision_trace.py`
- `backend/tests/test_forex_notification.py`
- `backend/tests/test_leader_*`

테스트를 읽을 때 확인할 포인트:

- 채팅 응답 구조
- trace/evidence 기록
- clarification 여부
- 권한 스코프
- decision_v2 구조
- forex/notification 시나리오

---

## 작업 시 주의사항

1. Agent 추가만 하고 `_AGENT_REGISTRY`를 갱신하지 않으면 Leader가 실행하지 못한다.
2. Tool을 추가할 때는 `mock-api`, `tools_seed`, `mappings_seed`, 필요 테스트를 함께 수정해야 한다.
3. Trace 스키마를 건드리면 목록/상세 API와 관리자 화면 영향 범위를 같이 봐야 한다.
4. `AUTH_ENABLED` 기본값이 false라 개발 중 인증 이슈가 가려질 수 있다.
5. 프론트 포트는 `3000`이 아니라 도커 외부 기준 `13000`이다.
6. Postgres 외부 포트는 `5433`이 아니라 현재 `15433`이다.

---

## 현재 구현 상태 한 줄 요약

이 저장소는 “대출 상담용 단일 MVP”가 아니라, 금융 상담 멀티에이전트 플랫폼의 확장형 데모에 가깝다. 문서나 수정 작업은 반드시 현재 코드와 `docker-compose.yml`, seed 파일, 테스트를 기준으로 맞춘다.
