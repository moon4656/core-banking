# Codex용 Phase 0 단기 실행 프롬프트

작성일: 2026-06-09

---

## 사용 방법

아래 텍스트 블록을 Codex에 그대로 입력한다.

---

```text
Read these files first, in order:
1. docs/AI_Agent_PRD.md
2. docs/AI_Agent_TECH_SPEC.md
3. docs/AI_Agent_TECH_SPEC_TASK.md

Then execute Phase 0 only.

Phase 0 scope:
- Create docker-compose.yml (services: backend, postgres, redis, pgadmin, mock-api; postgres healthcheck included)
- Create .env.example
- Create backend/Dockerfile
- Create backend/requirements.txt (fastapi, uvicorn[standard], sqlalchemy, alembic, pydantic[dotenv], httpx, redis, structlog, pytest, pytest-asyncio)
- Create backend/app/main.py (GET /health → {"status": "ok", "service": "backend"})
- Create backend/app/core/config.py (Pydantic BaseSettings, reads DATABASE_URL, REDIS_URL, MOCK_API_URL from env)
- Create mock-api/Dockerfile
- Create mock-api/requirements.txt
- Create mock-api/main.py (GET /health → {"status": "ok", "service": "mock-api"})
- Create README.md (draft)

Forbidden in Phase 0:
- No DB models
- No Alembic
- No seed data
- No agents
- No Knowledge/Tool/Trace services
- No Chat API
- No Neo4j, Graph DB, RDF, OWL, SPARQL
- No Phase 1+ work

Verification:
docker compose up -d --build
curl http://localhost:8000/health  ← must return {"status": "ok", "service": "backend"}
curl http://localhost:8010/health  ← must return {"status": "ok", "service": "mock-api"}

After completing Phase 0, create:
- docs/context/COMPACT_READY.md
- docs/context/CONTEXT_RESTORE.md
- docs/phase/PHASE_0_RESULT.md

Do NOT start Phase 1 automatically.
```
