import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    READONLY = "READONLY"


@dataclass(frozen=True)
class AuthContext:
    name: str
    role: Role


_ROLE_HIERARCHY: dict[Role, int] = {
    Role.READONLY: 1,
    Role.ANALYST: 2,
    Role.ADMIN: 3,
}


def _resolve_role(api_key: str | None) -> Role | None:
    if not api_key:
        return None
    key_map = {
        settings.API_KEY_ADMIN: Role.ADMIN,
        settings.API_KEY_ANALYST: Role.ANALYST,
        settings.API_KEY_READONLY: Role.READONLY,
    }
    return key_map.get(api_key)


def resolve_role(api_key: str | None) -> Role | None:
    if not settings.AUTH_ENABLED:
        return Role.ADMIN
    return _resolve_role(api_key)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_session_token(name: str, role: Role) -> str:
    payload = {
        "sub": name,
        "role": role.value,
        "exp": int(time.time()) + settings.SESSION_TTL_SECONDS,
    }
    payload_encoded = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.SESSION_SECRET.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_encoded}.{_b64url_encode(signature)}"


def verify_session_token(token: str) -> tuple[str, Role] | None:
    try:
        payload_encoded, signature_encoded = token.split(".", 1)
        expected_signature = hmac.new(
            settings.SESSION_SECRET.encode("utf-8"),
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_signature = _b64url_decode(signature_encoded)
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        payload = json.loads(_b64url_decode(payload_encoded).decode("utf-8"))
        if int(payload["exp"]) < int(time.time()):
            return None

        role = Role(payload["role"])
        return str(payload["sub"]), role
    except Exception:
        return None


def extract_name_from_token(token: str) -> str | None:
    """서명 검증 없이 토큰 payload의 sub(이름)만 추출한다. 표시 목적 전용."""
    try:
        payload_encoded = token.split(".")[0]
        payload = json.loads(_b64url_decode(payload_encoded).decode("utf-8"))
        return str(payload["sub"]) or None
    except Exception:
        return None


def _resolve_authenticated_role(
    api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str, Role] | None:
    if credentials and credentials.scheme.lower() == "bearer":
        verified = verify_session_token(credentials.credentials)
        if verified is not None:
            return verified

    role = resolve_role(api_key)
    if role is None:
        return None
    return "authenticated-user", role


def _resolve_authenticated_context(
    api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthContext | None:
    resolved = _resolve_authenticated_role(api_key, credentials)
    if resolved is None:
        return None
    name, role = resolved
    return AuthContext(name=name, role=role)


def _check(
    required_role: Role,
    api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> Role:
    resolved = _resolve_authenticated_role(api_key, credentials)

    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다. X-API-Key 또는 Bearer 토큰을 확인하세요.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _, role = resolved
    if _ROLE_HIERARCHY[role] < _ROLE_HIERARCHY[required_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"이 기능은 {required_role.value} 이상의 권한이 필요합니다. 현재 권한: {role.value}",
        )

    return role


def _check_context(
    required_role: Role,
    api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthContext:
    context = _resolve_authenticated_context(api_key, credentials)

    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다. X-API-Key 또는 Bearer 토큰을 확인하세요.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if _ROLE_HIERARCHY[context.role] < _ROLE_HIERARCHY[required_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"이 기능은 {required_role.value} 이상의 권한이 필요합니다. 현재 권한: {context.role.value}",
        )

    return context


def require_readonly(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> Role:
    return _check(Role.READONLY, api_key, credentials)


def require_analyst(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> Role:
    return _check(Role.ANALYST, api_key, credentials)


def require_admin(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> Role:
    return _check(Role.ADMIN, api_key, credentials)


def require_readonly_context(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> AuthContext:
    return _check_context(Role.READONLY, api_key, credentials)


def require_analyst_context(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> AuthContext:
    return _check_context(Role.ANALYST, api_key, credentials)
