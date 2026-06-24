# main.py — FastAPI 애플리케이션 진입점
#
# [서비스 구조]
#   이 파일에서 FastAPI 앱을 생성하고, 모든 라우터를 등록한다.
#   실제 비즈니스 로직은 각 라우터 파일과 하위 모듈에 있다.
#
# [등록된 라우터]
#   /api/v1/ai/      → ai_gateway_router  : 채팅 API (POST /chat), Trace 조회
#   /api/v1/knowledge → knowledge_router  : concept 검색, Agent/API 목록 조회
#   /api/v1/agents/  → agent_router       : Agent 목록/상세 조회
#   /api/v1/tools/   → tool_router        : Tool 목록 조회, Tool 직접 호출
#
# [정적 파일]
#   /         → backend/app/static/index.html (ChatGPT 스타일 챗봇 UI)
#   /static/  → backend/app/static/ 디렉터리 전체
#
# [lifespan]
#   FastAPI의 lifespan 컨텍스트 매니저를 사용해 시작/종료 시 로그를 남긴다.
#   DB 연결 초기화나 캐시 워밍업이 필요하면 여기에 추가한다.

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import agent as agent_router
from app.api.routes import ai_gateway as ai_gateway_router
from app.api.routes import auth as auth_router
from app.api.routes import knowledge as knowledge_router
from app.api.routes import decisions as decisions_router
from app.api.routes import leader_evaluation as leader_evaluation_router
from app.api.routes import monitoring as monitoring_router
from app.api.routes import leader_monitor as leader_monitor_router
from app.api.routes import admin as admin_router
from app.api.routes import tool as tool_router
from app.api.routes import trace as trace_router
from app.api.routes import concept_eval as concept_eval_router
from app.core.config import settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 로그 — Docker 로그에서 시작 확인용
    logger.info("startup", service="backend", environment=settings.ENVIRONMENT)
    yield
    # 서버 종료 시 로그 — Ctrl+C 또는 docker compose stop 시 실행
    logger.info("shutdown", service="backend")


app = FastAPI(
    title="AI Agent MVP",
    description="Docker 기반 멀티에이전트 AI 서비스 MVP",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 설정 — 브라우저에서 다른 origin(포트)의 API를 호출할 때 필요하다.
# MVP에서는 allow_origins=["*"]로 전체 허용한다. 운영 환경에서는 도메인을 명시해야 한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 — 각 파일의 prefix가 URL 경로가 된다
# 예: ai_gateway_router의 prefix="/api/v1/ai" + @router.post("/chat") → POST /api/v1/ai/chat
app.include_router(ai_gateway_router.router)
app.include_router(trace_router.router)       # /api/v1/ai/traces/{id}, /events, /evidence
app.include_router(auth_router.router)
app.include_router(knowledge_router.router)
app.include_router(agent_router.router)
app.include_router(tool_router.router)
app.include_router(decisions_router.router)
app.include_router(leader_evaluation_router.router)
app.include_router(monitoring_router.router)
app.include_router(leader_monitor_router.router)   # /api/v1/leader-agent/traces
app.include_router(admin_router.router)
app.include_router(concept_eval_router.router)

# 정적 파일 서빙 설정
# __file__ = 현재 파일(main.py)의 경로 → parent = app/ 디렉터리 → static/ 디렉터리
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/", include_in_schema=False)
def chat_ui():
    """챗봇 UI 진입점. http://localhost:18000/ 에서 접근 가능."""
    return FileResponse(_static_dir / "index.html")


@app.get("/monitor", include_in_schema=False)
def monitor_ui():
    """Leader Agent 모니터링 화면. http://localhost:18000/monitor 에서 접근 가능."""
    return FileResponse(_static_dir / "monitor.html")


@app.get("/health")
def health_check():
    """
    서비스 헬스 체크 엔드포인트.

    Docker Compose의 healthcheck, 로드밸런서, 모니터링 시스템이 이 URL을 주기적으로 호출한다.
    DB 연결 확인 등 추가 체크가 필요하면 이 함수에 로직을 추가한다.
    """
    return {"status": "ok", "service": "backend"}
