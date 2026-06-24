# Claude Code용 Phase 0 상세 실행 프롬프트

작성일: 2026-06-09

---

## 사용 방법

아래 텍스트 블록을 Claude Code 대화창에 그대로 붙여넣는다.

---

```text
너는 시니어 Python/FastAPI 아키텍트이자 Docker 환경 설계 전문가다.
Docker Compose 기반 멀티에이전트 AI 서비스 MVP의 Phase 0을 담당한다.

---

## 반드시 읽을 문서 (이 순서로 읽어라)

1. docs/AI_Agent_PRD.md
2. docs/AI_Agent_TECH_SPEC.md
3. docs/AI_Agent_TECH_SPEC_TASK.md
4. docs/FINAL_PROJECT_STRUCTURE.md
5. CLAUDE.md

문서를 읽지 않고 작업을 시작하지 마라.

---

## Phase 0 목표

Docker Compose 환경에서 FastAPI backend(포트 8000)와 mock-api(포트 8010)가 각각
GET /health 엔드포인트로 정상 응답하는 상태를 만든다.

---

## 작업 범위 (이 파일들만 생성한다)

```
docker-compose.yml
.env.example
README.md (초안)
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

### docker-compose.yml 작성 기준
- services: backend, postgres, redis, pgadmin, mock-api
- postgres에 healthcheck 포함 (pg_isready 기반)
- backend의 depends_on에 postgres condition: service_healthy 포함
- worker, admin-ui, prometheus는 주석 처리로 MVP 제외 명시
- volumes: postgres_data

### .env.example 내용
```
POSTGRES_DB=ai_agent_db
POSTGRES_USER=ai_agent
POSTGRES_PASSWORD=ai_agent_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://ai_agent:ai_agent_password@postgres:5432/ai_agent_db
REDIS_URL=redis://redis:6379
MOCK_API_URL=http://mock-api:8010
ENVIRONMENT=development
```

### backend/app/main.py 작성 기준
- FastAPI() 앱 생성
- GET /health → {"status": "ok", "service": "backend"}
- CORSMiddleware 추가 (개발용 allow_origins=["*"])
- lifespan 이벤트에서 startup 로그 출력
- /docs, /redoc 자동 활성화

### backend/app/core/config.py 작성 기준
- Pydantic BaseSettings 사용
- DATABASE_URL, REDIS_URL, MOCK_API_URL, ENVIRONMENT 읽기
- model_config = SettingsConfigDict(env_file=".env")

### mock-api/main.py 작성 기준
- FastAPI() 앱 생성
- GET /health → {"status": "ok", "service": "mock-api"}
- 나머지 Mock endpoint는 Phase 5에서 추가 (이번에는 /health만)

---

## 금지 범위

아래는 Phase 0에서 절대 구현하지 않는다.

- DB 모델 (SQLAlchemy 모델 파일) 구현 금지
- Alembic 마이그레이션 구성 금지
- Seed 데이터 구현 금지
- Agent 클래스 구현 금지
- Knowledge Metadata Service 구현 금지
- Tool/API Hub 구현 금지
- Trace/Evidence 구현 금지
- Chat API 구현 금지
- Neo4j, RDF/OWL, SPARQL, Graph DB 관련 금지
- Kubernetes 관련 내용 금지
- Phase 1 이상 작업 선행 금지

---

## 실행 및 검증 명령

작업 완료 후 반드시 다음 명령을 실행하고 결과를 확인한다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8010/health
```

---

## 완료 조건

다음 결과가 모두 확인되어야 Phase 0 완료다.

1. docker compose ps → 전체 서비스 Up 상태
2. curl http://localhost:8000/health → {"status": "ok", "service": "backend"}
3. curl http://localhost:8010/health → {"status": "ok", "service": "mock-api"}
4. http://localhost:8000/docs → Swagger UI 접속 가능
5. http://localhost:5050 → pgadmin 접속 가능

---

## Phase 종료 시 반드시 생성할 문서

Phase 0 완료 조건 달성 후 다음 문서를 생성한다.

### docs/context/COMPACT_READY.md
현재 Phase(0 완료), 다음 Phase(1), 완료 항목, 다음 Phase 진입 조건 기록

### docs/context/CONTEXT_RESTORE.md
프로젝트 기술 스택, Phase 0 결과(생성 파일, 확인 URL), Phase 1 작업 내용, 핵심 원칙 기록

### docs/phase/PHASE_0_RESULT.md
완료된 작업 목록, 생성된 파일 목록, 검증 결과, 발생한 이슈와 해결 방법 기록

---

## 다음 단계 안내

Phase 0 완료 후 사용자에게 결과를 보고하고 대기한다.

자동으로 Phase 1을 시작하지 않는다.

사용자로부터 "Phase 1 시작" 명시적 승인을 받은 뒤에만 Phase 1으로 진행한다.
```
