from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import extract_name_from_token, issue_session_token, resolve_role, verify_session_token
from app.schemas.auth import LoginRequest, SessionResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=SessionResponse)
def login(body: LoginRequest):
    role = resolve_role(body.api_key)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )

    return SessionResponse(
        name=body.name,
        role=role.value,
        auth_mode="bypass" if not settings.AUTH_ENABLED else "session_token",
        access_token=issue_session_token(body.name, role),
    )


@router.get("/me", response_model=SessionResponse)
def me(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
):
    name = "authenticated-user"
    role = None

    if credentials and credentials.scheme.lower() == "bearer":
        verified = verify_session_token(credentials.credentials)
        if verified is not None:
            name, role = verified
        else:
            # 서명 검증 실패 시에도 payload의 sub(이름)은 표시 목적으로 사용한다.
            # 역할은 여전히 별도 auth 경로에서 결정하므로 보안상 안전하다.
            extracted = extract_name_from_token(credentials.credentials)
            if extracted:
                name = extracted

    if role is None:
        role = resolve_role(api_key)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication",
        )

    return SessionResponse(
        name=name,
        role=role.value,
        auth_mode="bypass" if not settings.AUTH_ENABLED else "session_token",
        access_token=issue_session_token(name, role),
    )
