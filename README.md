# core-banking

FastAPI 백엔드와 Next.js 프론트엔드로 구성된 멀티에이전트 금융 상담 데모 프로젝트입니다.  
Leader Agent가 사용자 질문을 분석하고, 개념 기반 라우팅과 Tool 호출을 통해 대출, 외환, 알림 도메인 응답을 조합합니다.

## 주요 기능

- 대출 상품, 금리, 우대금리, 정책, 필요서류 안내
- 금리 시뮬레이션, 자격 사전 점검, 개인화 금리 조회
- 상담 이력 / 문서 검색
- 환율 조회, 환전 계산, 해외송금, 외화예금 조회
- 알림 규칙 조회와 Mock 알림 발송
- Trace / Evidence / Decision Trace 기록 및 조회
- 관리자 / 모니터링 / 의사결정 시각화 화면

## 아키텍처

핵심 흐름은 다음과 같습니다.

```text
Client
  -> Frontend (Next.js) / Swagger / Static UI
  -> Backend FastAPI
  -> LeaderAgent
     -> intent 분석
     -> concept 탐지 및 확장
     -> DB 기반 agent routing
     -> execution planning
     -> Sub Agent 실행
     -> ToolGateway를 통한 Mock API 호출
     -> evidence 저장 / rerank / answer compose / validation
  -> ChatResponse + trace/evidence metadata
```

핵심 원칙:

- Agent 선택은 `agent_concept_mapping` 기반입니다.
- Tool 호출은 직접 URL 호출이 아니라 `ToolGateway`만 사용합니다.
- 요청과 근거는 Trace / Evidence로 남깁니다.

## Agent 구성

현재 활성 Agent:

- `LEADER_AGENT`
- `PRODUCT_AGENT`
- `RATE_AGENT`
- `POLICY_AGENT`
- `SEARCH_AGENT`
- `FOREX_AGENT`
- `NOTIFICATION_AGENT`

대표 구현 파일:

- [leader.py](/C:/temp/core-banking/backend/app/agents/leader.py)
- [agent_registry.py](/C:/temp/core-banking/backend/app/agents/agent_registry.py)
- [tools_seed.py](/C:/temp/core-banking/backend/app/seed/tools_seed.py)

## 기술 스택

Backend:

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- httpx
- OpenAI SDK
- pytest

Frontend:

- Next.js 15
- React 18
- TypeScript
- MUI
- TanStack Query

## 디렉터리 구조

```text
core-banking/
  backend/
    app/
      agents/
      api/routes/
      core/
      knowledge/
      models/
      schemas/
      seed/
      services/
      tools/
      trace/
      static/
    tests/
  frontend/
    src/app/
    src/components/
    src/lib/
    src/types/
  mock-api/
  docs/
  data/
  docker-compose.yml
```

## 빠른 시작

### 1. 환경 변수 준비

루트에 `.env` 파일을 준비합니다.

```bash
cp .env.example .env
```

Windows PowerShell에서는:

```powershell
Copy-Item .env.example .env
```

### 2. 컨테이너 실행

```bash
docker compose up -d --build
```

### 3. 마이그레이션 적용

```bash
docker compose exec backend alembic upgrade head
```

### 4. Seed 데이터 적재

```bash
docker compose exec backend python -m app.seed.run_seed
```

### 5. 헬스 체크

```bash
curl http://localhost:18000/health
curl http://localhost:18010/health
```

## 접속 주소

- Frontend: `http://localhost:13000`
- Backend API: `http://localhost:18000`
- Swagger UI: `http://localhost:18000/docs`
- Mock API: `http://localhost:18010`
- pgAdmin: `http://localhost:15050`
- PostgreSQL: `localhost:15433`

## 주요 API

채팅:

- `POST /api/v1/ai/chat`
- `GET /api/v1/ai/scenarios`

Trace:

- `GET /api/v1/ai/traces`
- `GET /api/v1/ai/traces/{request_id}`
- `GET /api/v1/ai/traces/{request_id}/events`
- `GET /api/v1/ai/traces/{request_id}/evidence`

관리/운영:

- `GET /api/v1/admin/cache/intent-patterns`
- `DELETE /api/v1/admin/cache/intent-patterns`

카탈로그/메타데이터:

- `GET /api/v1/knowledge/...`
- `GET /api/v1/tools`
- `POST /api/v1/tools/invoke`
- `GET /api/v1/agents/...`

## 채팅 요청 예시

```http
POST /api/v1/ai/chat
Content-Type: application/json

{
  "message": "신용대출 금리 알려줘",
  "session_id": "demo-session-1"
}
```

응답에는 일반적으로 아래 정보가 포함됩니다.

- `request_id`
- `plan`
- `results`
- `answer`
- `intent`
- `memory_turns`
- `trace_count`
- `evidence_count`
- `decision_v2`

## 인증

인증 방식:

- `X-API-Key`
- `Authorization: Bearer <session-token>`

권한:

- `READONLY`
- `ANALYST`
- `ADMIN`

개발 기본값:

- `AUTH_ENABLED=false`이면 인증 없이 내부적으로 관리자 권한처럼 동작합니다.
- 운영 검증 시에는 `AUTH_ENABLED=true`와 각 API Key를 명시적으로 설정하는 것이 좋습니다.

## 환경 변수

대표 환경 변수:

```env
POSTGRES_DB=ai_agent_db
POSTGRES_USER=ai_agent
POSTGRES_PASSWORD=ai_agent_password
DATABASE_URL=postgresql://ai_agent:ai_agent_password@postgres:5432/ai_agent_db
REDIS_URL=redis://redis:6379
MOCK_API_URL=http://mock-api:8010
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
AUTH_ENABLED=false
API_KEY_ADMIN=
API_KEY_ANALYST=
API_KEY_READONLY=
SESSION_SECRET=change-me-session-secret
SESSION_TTL_SECONDS=1800
APP_TIMEZONE=Asia/Seoul
```

## 테스트

백엔드 테스트 실행:

```bash
docker compose exec backend pytest
```

중요 테스트 범위:

- chat 응답 구조
- trace / evidence 기록
- 인증 / 권한
- decision trace
- forex / notification 시나리오
- validation / disclaimer

## 개발 메모

- 실제 Leader 구현 파일은 `leader_agent.py`가 아니라 `backend/app/agents/leader.py`입니다.
- Agent 추가 시 `_AGENT_REGISTRY`, seed, mapping, 테스트를 함께 수정해야 합니다.
- Tool 추가 시 `mock-api/main.py`와 `backend/app/seed/tools_seed.py`를 함께 봐야 합니다.
- 이 저장소는 초기 대출 MVP 문서보다 범위가 넓으므로, 문서 수정은 항상 코드와 테스트 기준으로 맞추는 것이 안전합니다.
