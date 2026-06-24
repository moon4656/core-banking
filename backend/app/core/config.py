# config.py — 서비스 전체 환경 변수 관리
#
# pydantic-settings의 BaseSettings를 상속하면:
#   1. .env 파일을 자동으로 읽는다 (env_file=".env")
#   2. 실제 환경 변수(os.environ)가 .env보다 우선 적용된다
#   3. 미설정 변수는 여기서 정의한 기본값을 사용한다
#
# Docker Compose에서는 docker-compose.yml의 environment 블록이
# 컨테이너 환경 변수로 주입되므로 .env 없이도 동작한다.
#
# [주의] 비밀값(패스워드 등)을 코드에 직접 쓰지 말 것.
#        프로덕션에서는 Docker Secrets나 환경 변수 주입으로 관리한다.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL 접속 정보
    # POSTGRES_HOST는 Docker Compose 네트워크에서 서비스명 "postgres"를 가리킨다
    POSTGRES_DB: str = "ai_agent_db"
    POSTGRES_USER: str = "ai_agent"
    POSTGRES_PASSWORD: str = "ai_agent_password"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # SQLAlchemy가 사용하는 전체 DB 접속 URL
    # 형식: postgresql://<user>:<password>@<host>:<port>/<db>
    DATABASE_URL: str = "postgresql://ai_agent:ai_agent_password@postgres:5432/ai_agent_db"

    # Redis URL — 현재 MVP에서는 예약만 해뒀고 캐시로 아직 사용하지 않는다
    REDIS_URL: str = "redis://redis:6379"

    # Mock API 서비스 주소 — 컨테이너 내부 네트워크에서 "mock-api" 서비스명으로 접근
    # 로컬 직접 실행 시에는 http://localhost:18010 으로 변경 필요
    MOCK_API_URL: str = "http://mock-api:8010"

    ENVIRONMENT: str = "development"
    APP_TIMEZONE: str = "Asia/Seoul"

    # OpenAI API 키 — LLM 응답 생성에 사용
    # .env 파일에 OPENAI_API_KEY=sk-... 형식으로 설정
    OPENAI_API_KEY: str = ""

    # OpenAI 모델명 — .env에서 OPENAI_MODEL=gpt-4o-mini 등으로 변경 가능
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ─────────────────────────────────────────────────────────────
    # API Key 인증 설정 (security.py 와 함께 동작)
    # ─────────────────────────────────────────────────────────────
    # AUTH_ENABLED=false 로 설정하면 개발 환경에서 인증 없이 전체 허용
    AUTH_ENABLED: bool = False

    # 역할별 API 키 — .env 또는 환경변수로 반드시 설정할 것
    # 생성 예: openssl rand -hex 32
    # 기본값 빈 문자열 → AUTH_ENABLED=true 상태에서 미설정이면 인증 불가
    API_KEY_ADMIN:    str = ""
    API_KEY_ANALYST:  str = ""
    API_KEY_READONLY: str = ""

    SESSION_SECRET: str = "change-me-session-secret"
    SESSION_TTL_SECONDS: int = 1800


# 모듈 어디서든 settings.DATABASE_URL 처럼 바로 임포트해서 사용한다
settings = Settings()
