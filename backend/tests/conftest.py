# conftest.py — pytest 공통 fixture 정의 파일
#
# pytest는 이 파일을 자동으로 인식해 모든 테스트 파일에서 fixture를 공유한다.
# fixture는 테스트 함수의 파라미터 이름으로 자동 주입된다.
# 예: def test_something(db, client): ...  → db, client fixture 자동 주입
#
# [테스트 실행 방법]
#   docker compose exec backend pytest -v
#
# [전제 조건]
#   - PostgreSQL에 테이블이 생성되어 있어야 한다 (alembic upgrade head)
#   - Seed 데이터가 등록되어 있어야 한다 (python -m app.seed.run_seed)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app

# 실제 PostgreSQL에 연결하는 테스트용 엔진
# 컨테이너 내부에서 실행되므로 settings.DATABASE_URL (postgres:5432) 그대로 사용
_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture
def db():
    """
    각 테스트에 독립적인 DB 세션을 제공한다.
    테스트 종료 후 세션을 닫아 커넥션 풀로 반환한다.

    주의: record_event/record_evidence는 내부에서 db.commit()을 호출하므로
    테스트 데이터가 실제 DB에 기록된다.
    test_chat.py에서는 테스트 후 cleanup fixture로 데이터를 삭제한다.
    """
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """
    FastAPI TestClient — 실제 HTTP 서버 없이 API 엔드포인트를 테스트한다.

    app.dependency_overrides로 get_db 의존성을 테스트 세션으로 교체한다.
    TestClient 컨텍스트 안에서 lifespan 이벤트(startup/shutdown)도 실행된다.
    테스트 종료 후 overrides를 초기화해 다른 테스트에 영향을 주지 않는다.
    """
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(db, monkeypatch):
    """Enable auth and inject stable test API keys for protected-route tests."""
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEY_ADMIN", "test-admin-key")
    monkeypatch.setattr(settings, "API_KEY_ANALYST", "test-analyst-key")
    monkeypatch.setattr(settings, "API_KEY_READONLY", "test-readonly-key")

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
