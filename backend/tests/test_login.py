def test_auth_login_returns_server_role(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "name": "portal-user",
            "apiKey": "test-analyst-key",
        },
        headers={"X-API-Key": "test-analyst-key"},
    )

    # In most test runs AUTH_ENABLED is false, so this endpoint still succeeds.
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "portal-user"
    assert "role" in body
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_auth_me_invalid_key_returns_401(auth_client):
    resp = auth_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": "wrong-key-xyz"},
    )
    assert resp.status_code == 401


def test_auth_me_admin_key_returns_role(auth_client):
    resp = auth_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMIN"


def test_auth_me_bearer_token_returns_role(auth_client):
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={
            "name": "portal-user",
            "apiKey": "test-analyst-key",
        },
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    me_resp = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "ANALYST"


def test_knowledge_bearer_token_succeeds(auth_client):
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={
            "name": "portal-user",
            "apiKey": "test-readonly-key",
        },
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    resp = auth_client.get(
        "/api/v1/knowledge/concepts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
