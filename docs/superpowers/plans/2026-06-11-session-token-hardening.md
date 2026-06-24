# Session Token Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the current signed session-token flow with a 30-minute TTL, immediate redirect to login on expiry, clearer session-expiry messaging, and stronger environment-based secret handling.

**Architecture:** Keep the existing signed bearer-token approach instead of introducing refresh tokens or a server-side session store. Tighten the backend token validation and response semantics, then update the frontend login and protected-layout flow so expired sessions are handled consistently and visibly.

**Tech Stack:** FastAPI, Pydantic, Next.js, React, React Query, local session storage

---

### Task 1: Add backend expiry-focused auth tests

**Files:**
- Modify: `backend/tests/test_login.py`
- Test: `backend/tests/test_login.py`

- [ ] Add a failing test for a valid bearer token returned by login.

```python
def test_auth_login_returns_server_role(auth_client):
    resp = auth_client.post(
        "/api/v1/auth/login",
        json={"name": "portal-user", "apiKey": "test-analyst-key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
```

- [ ] Add a failing test for `auth/me` with a bearer token.

```python
def test_auth_me_bearer_token_returns_role(auth_client):
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"name": "portal-user", "apiKey": "test-analyst-key"},
    )
    token = login_resp.json()["access_token"]

    me_resp = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "ANALYST"
```

- [ ] Add a failing test for a protected API call using bearer auth.

```python
def test_knowledge_bearer_token_succeeds(auth_client):
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"name": "portal-user", "apiKey": "test-readonly-key"},
    )
    token = login_resp.json()["access_token"]

    resp = auth_client.get(
        "/api/v1/knowledge/concepts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
```

- [ ] Run the auth test file to verify the new cases fail for the right reason.

Run: `python -m pytest backend/tests/test_login.py -q`
Expected: FAIL on missing token fields and missing bearer-auth support.

### Task 2: Tighten backend token security behavior

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/routes/auth.py`

- [ ] Set the session TTL to 1800 seconds and make the secret clearly environment-driven.

```python
SESSION_SECRET: str = "change-me-session-secret"
SESSION_TTL_SECONDS: int = 1800
```

- [ ] Implement or refine signed token helpers so they carry subject, role, and expiry.

```python
def issue_session_token(name: str, role: Role) -> str:
    payload = {
        "sub": name,
        "role": role.value,
        "exp": int(time.time()) + settings.SESSION_TTL_SECONDS,
    }
    ...
```

- [ ] Implement token verification that rejects invalid signatures and expired tokens.

```python
def verify_session_token(token: str) -> tuple[str, Role] | None:
    ...
    if int(payload["exp"]) < int(time.time()):
        return None
    return str(payload["sub"]), Role(payload["role"])
```

- [ ] Update the shared auth resolution logic so bearer tokens are accepted on protected APIs before any fallback auth path.

```python
def _resolve_authenticated_role(
    api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str, Role] | None:
    if credentials and credentials.scheme.lower() == "bearer":
        verified = verify_session_token(credentials.credentials)
        if verified is not None:
            return verified
    ...
```

- [ ] Update login and me responses to return `access_token`, `token_type`, and a consistent `auth_mode`.

```python
return SessionResponse(
    name=body.name,
    role=role.value,
    auth_mode="bypass" if not settings.AUTH_ENABLED else "session_token",
    access_token=issue_session_token(body.name, role),
)
```

- [ ] Run the login tests again to verify they pass.

Run: `python -m pytest backend/tests/test_login.py -q`
Expected: PASS

### Task 3: Update frontend session storage and API client

**Files:**
- Modify: `frontend/src/lib/session.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] Change the stored session shape from raw API-key usage to bearer-token usage.

```ts
export type UserSession = {
  name: string;
  role: AppRole;
  accessToken: string;
  authMode: string;
  tokenType: string;
};
```

- [ ] Update the shared API client to send `Authorization: Bearer <token>` for normal portal requests.

```ts
headers: {
  "Content-Type": "application/json",
  ...(session?.accessToken
    ? { Authorization: `${session.tokenType} ${session.accessToken}` }
    : {}),
},
```

- [ ] Keep login using `X-API-Key` only for the initial exchange.

```ts
export async function authLogin(name: string, apiKey: string) {
  return fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({ name, apiKey }),
  });
}
```

- [ ] Run the frontend build to catch type issues.

Run: `npm run build`
Expected: PASS or type errors only in the touched files.

### Task 4: Improve login and protected-screen expiry handling

**Files:**
- Modify: `frontend/src/app/login/page.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/components/layout/Topbar.tsx`

- [ ] Update login so the server-derived role and token are stored, not a user-selected role.

```ts
const session = await authLogin(values.name, values.apiKey);
setStoredSession({
  name: session.name,
  role: session.role,
  accessToken: session.access_token,
  authMode: session.auth_mode,
  tokenType: session.token_type,
});
```

- [ ] Add protected-layout validation through `GET /api/v1/auth/me`.

```ts
const profile = await apiGet<AuthSessionResponse>("/api/v1/auth/me");
setStoredSession({
  name: profile.name,
  role: profile.role,
  accessToken: profile.access_token,
  authMode: profile.auth_mode,
  tokenType: profile.token_type,
});
```

- [ ] On invalid or expired session, clear storage and redirect to `/login?reason=expired`.

```ts
clearStoredSession();
router.replace("/login?reason=expired");
```

- [ ] Update the login screen to detect `reason=expired` and show the agreed message.

```ts
setError("세션이 만료되었습니다. 다시 로그인해 주세요.");
```

- [ ] Keep logout simple: clear local session and redirect to login.

```ts
clearStoredSession();
router.push("/login");
```

- [ ] Run the frontend build again after the UI/auth flow changes.

Run: `npm run build`
Expected: PASS

### Task 5: Refresh documentation and environment guidance

**Files:**
- Modify: `docs/FRONTEND_PORTAL.md`
- Modify: `.env.example`
- Modify: `backend/.env`-related examples if present

- [ ] Document the 30-minute session TTL and immediate login redirect on expiry.

```md
- Session TTL: 30 minutes
- On expiry: clear session and redirect to `/login`
```

- [ ] Document that `SESSION_SECRET` must be set explicitly in non-development environments.

```env
SESSION_SECRET=replace-with-a-long-random-secret
SESSION_TTL_SECONDS=1800
```

- [ ] Mention that the portal now uses bearer tokens after the initial login exchange.

```md
- `POST /api/v1/auth/login` exchanges `X-API-Key` for a signed bearer token
- Normal portal requests use `Authorization: Bearer <token>`
```

### Task 6: Final verification

**Files:**
- Verify: `backend/app/core/security.py`
- Verify: `backend/app/api/routes/auth.py`
- Verify: `frontend/src/lib/api.ts`
- Verify: `frontend/src/components/layout/AppShell.tsx`
- Verify: `frontend/src/app/login/page.tsx`
- Verify: `docs/FRONTEND_PORTAL.md`

- [ ] Run backend auth tests.

Run: `python -m pytest backend/tests/test_login.py -q`
Expected: PASS

- [ ] Run frontend production build.

Run: `npm run build`
Expected: PASS

- [ ] Search for leftover direct API-key use in normal portal request paths.

Run: `rg -n "X-API-Key|apiKey" frontend/src`
Expected: only the login exchange and user input field remain.
