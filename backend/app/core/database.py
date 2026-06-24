# database.py — SQLAlchemy DB 연결 및 세션 관리
#
# [구성 요소]
#   engine       : 실제 DB 연결 풀을 관리한다. 애플리케이션 생명주기 동안 1개만 생성한다.
#   SessionLocal : 요청마다 새 세션을 만드는 팩토리. 세션은 트랜잭션 단위로 사용한다.
#   Base         : 모든 SQLAlchemy 모델이 상속하는 기반 클래스.
#                  alembic upgrade head 시 Base.metadata로 테이블 정의를 읽는다.
#
# [pool_pre_ping=True 이유]
#   PostgreSQL이 idle 커넥션을 끊은 경우 다음 요청에서 오류가 발생할 수 있다.
#   pool_pre_ping은 쿼리 전에 커넥션 유효성을 확인해 자동으로 재연결한다.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# autocommit=False: 명시적으로 commit()을 호출해야 변경이 반영된다. 실수로 인한 부분 저장을 방지한다.
# autoflush=False: query 전에 자동 flush(DB 반영)를 하지 않는다. 명시적 제어를 위해 끈다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI 의존성 주입용 DB 세션 제너레이터.

    [사용법]
        from app.core.database import get_db
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    [생명주기]
        요청 시작 → 세션 생성 → 라우트 함수 실행 → 요청 종료 → 세션 닫힘
        예외 발생 시에도 finally 블록에서 반드시 close()가 호출된다.

    [yield 패턴]
        yield 이전: 라우트 함수에 세션 전달
        yield 이후: 요청이 끝난 뒤 실행되는 cleanup 코드
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # 세션을 닫아 커넥션 풀로 반환한다. 닫지 않으면 풀이 고갈돼 서비스가 멈출 수 있다.
        db.close()
