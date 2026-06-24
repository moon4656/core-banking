# Phase 0 실행 질의서

작성일: 2026-06-09

---

## 역할

너는 시니어 Python/FastAPI 아키텍트이다. Docker Compose 기반 멀티에이전트 AI 서비스 MVP의 Phase 0(프로젝트 기본 구조 및 Docker 구성)을 담당한다.

---

## 반드시 읽을 문서

작업 시작 전 다음 문서를 순서대로 읽어라.

```text
1. docs/AI_Agent_PRD.md
2. docs/AI_Agent_TECH_SPEC.md
3. docs/AI_Agent_TECH_SPEC_TASK.md
4. docs/FINAL_PROJECT_STRUCTURE.md
5. CLAUDE.md
```

---

## 목표

Docker Compose 환경에서 FastAPI backend와 mock-api가 각각 `/health` endpoint로 정상 응답하는 상태를 만든다.

---

## 작업 범위

다음 파일만 생성한다.

```text
docker-compose.yml
.env.example
README.md (초안)
backend/Dockerfile
backend/requirements.txt
backend/app/__init__.py
backend/app/main.py              ← /health endpoint 포함
backend/app/core/__init__.py
backend/app/core/config.py       ← Pydantic Settings 기반
mock-api/Dockerfile
mock-api/requirements.txt
mock-api/main.py                 ← /health endpoint 포함
```

---

## 금지 범위

Phase 0에서 절대 구현하지 않는다.

```text
- DB 모델 (SQLAlchemy 모델 파일) 구현 금지
- Alembic 마이그레이션 구성 금지
- Seed 데이터 구현 금지
- Agent 클래스 구현 금지
- Knowledge Metadata Service 구현 금지
- Tool/API Hub 구현 금지
- Trace/Evidence 구현 금지
- Chat API 구현 금지
- 온톨로지/Graph DB 관련 내용 구현 금지
- Phase 1 이상 작업 선행 금지
- Neo4j, RDF/OWL, SPARQL 관련 내용 금지
- Kubernetes 관련 내용 금지
```

---

## 생성 파일 상세

### docker-compose.yml
- services: backend, postgres, redis, pgadmin, mock-api
- postgres healthcheck 포함 (backend depends_on condition: service_healthy)
- worker, admin-ui, prometheus 주석 처리(MVP 제외 명시)
- volumes: postgres_data

### .env.example
```env
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

### backend/app/main.py
- FastAPI 앱 생성
- `/health` GET endpoint → `{"status": "ok", "service": "backend"}`
- lifespan 이벤트 (startup 로그)
- CORS 설정 (개발용 allow_origins=["*"])

### backend/app/core/config.py
- Pydantic BaseSettings 사용
- DATABASE_URL, REDIS_URL, MOCK_API_URL, ENVIRONMENT 환경변수 읽기
- `.env` 파일 자동 로딩

### mock-api/main.py
- FastAPI 앱 생성
- `/health` GET endpoint → `{"status": "ok", "service": "mock-api"}`
- 추가 endpoint는 Phase 5에서 구현

---

## 실행 명령

```bash
# .env 파일 생성
cp .env.example .env

# Docker Compose 빌드 및 실행
docker compose up -d --build

# 헬스 체크
curl http://localhost:8000/health
curl http://localhost:8010/health

# 로그 확인
docker compose logs backend
docker compose logs mock-api
```

---

## 완료 조건

다음 두 명령이 모두 성공 응답을 반환해야 한다.

```bash
curl http://localhost:8000/health
# 예상 응답: {"status": "ok", "service": "backend"}

curl http://localhost:8010/health
# 예상 응답: {"status": "ok", "service": "mock-api"}
```

추가 확인:

```text
- docker compose ps → 전체 서비스 Up 상태
- http://localhost:8000/docs → Swagger UI 접속 가능
- http://localhost:5050 → pgadmin 접속 가능
```

---

## Phase 종료 시 생성 문서

Phase 0 완료 후 반드시 다음 문서를 생성한다.

### docs/context/COMPACT_READY.md

```markdown
# COMPACT_READY

현재 Phase: 0 완료
다음 Phase: 1 (DB 모델 및 Alembic 마이그레이션)

## 완료 항목
- docker-compose.yml 생성
- backend /health 동작
- mock-api /health 동작
- .env.example 생성

## 다음 Phase 진입 조건
- Phase 0 승인 완료
- docker compose up 정상 동작 확인
```

### docs/context/CONTEXT_RESTORE.md

```markdown
# CONTEXT_RESTORE

프로젝트: Docker 기반 멀티에이전트 AI 서비스 MVP
현재 단계: Phase 1 시작 준비

## 기술 스택
- Python 3.11 / FastAPI / SQLAlchemy 2.x / Alembic / PostgreSQL 15 / Redis 7 / Pydantic v2

## Phase 0 결과
- docker-compose.yml: backend, postgres, redis, pgadmin, mock-api
- backend health: http://localhost:8000/health
- mock-api health: http://localhost:8010/health

## Phase 1 작업
- DB 모델 작성 (11개 테이블)
- Alembic 마이그레이션 설정
- alembic upgrade head 실행

## 핵심 원칙
- 온톨로지/Graph DB 제외
- concept_id 기반 라우팅
- Tool/API Hub 경유
- 모든 요청 Trace 저장
```

### docs/phase/PHASE_0_RESULT.md

완료된 작업, 생성된 파일, 테스트 결과, 이슈 및 해결 방법을 기록한다.

---

## 다음 단계 안내

Phase 0 완료 후 사용자 승인을 받은 뒤에만 Phase 1으로 진행한다.

**자동으로 Phase 1을 시작하지 않는다.**

Phase 1 시작 조건:
```text
1. curl http://localhost:8000/health 성공 확인
2. curl http://localhost:8010/health 성공 확인
3. 사용자로부터 "Phase 1 시작" 명시적 승인
```
