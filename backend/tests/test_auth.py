from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app


def test_chat_no_key_returns_401(auth_client):
    resp = auth_client.post("/api/v1/ai/chat", json={"message": "신용대출 금리"})
    assert resp.status_code == 401


def test_knowledge_no_key_returns_401(auth_client):
    resp = auth_client.get("/api/v1/knowledge/concepts")
    assert resp.status_code == 401


def test_chat_invalid_key_returns_401(auth_client):
    resp = auth_client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리"},
        headers={"X-API-Key": "wrong-key-xyz"},
    )
    assert resp.status_code == 401


def test_chat_readonly_key_returns_403(auth_client):
    resp = auth_client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리"},
        headers={"X-API-Key": "test-readonly-key"},
    )
    assert resp.status_code == 403


def test_tool_invoke_analyst_key_returns_403(auth_client):
    resp = auth_client.post(
        "/api/v1/tools/invoke",
        json={"api_id": "MOCK_RATE_LOOKUP", "params": {}},
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403


def test_concept_create_analyst_key_returns_403(auth_client):
    resp = auth_client.post(
        "/api/v1/knowledge/concepts",
        json={
            "concept_id": f"CONCEPT_AUTH_{uuid4().hex[:8]}",
            "name": "권한 테스트",
            "aliases": [],
        },
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403


def test_agent_mapping_create_analyst_key_returns_403(auth_client):
    resp = auth_client.post(
        "/api/v1/knowledge/agent-mappings",
        json={
            "agent_id": "RATE_AGENT",
            "concept_id": "CONCEPT_INTEREST_RATE",
            "priority": 0,
        },
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403


def test_alias_delete_analyst_key_returns_403(auth_client):
    resp = auth_client.delete(
        "/api/v1/knowledge/aliases/1",
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403


def test_chat_analyst_key_succeeds(auth_client):
    resp = auth_client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 알려줘"},
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 200
    assert "answer" in resp.json()


def test_chat_admin_key_succeeds(auth_client):
    resp = auth_client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 알려줘"},
        headers={"X-API-Key": "test-admin-key"},
    )
    assert resp.status_code == 200


def test_knowledge_readonly_key_succeeds(auth_client):
    resp = auth_client.get(
        "/api/v1/knowledge/concepts",
        headers={"X-API-Key": "test-readonly-key"},
    )
    assert resp.status_code == 200


def test_tool_invoke_admin_key_succeeds(auth_client):
    resp = auth_client.post(
        "/api/v1/tools/invoke",
        json={"api_id": "MOCK_RATE_LOOKUP", "params": {}},
        headers={"X-API-Key": "test-admin-key"},
    )
    assert resp.status_code == 200


def test_concept_create_admin_key_succeeds(auth_client):
    resp = auth_client.post(
        "/api/v1/knowledge/concepts",
        json={
            "concept_id": f"CONCEPT_AUTH_{uuid4().hex[:8]}",
            "name": "관리자 등록 테스트",
            "description": "auth test",
            "domain": "AUTH",
            "is_active": True,
            "aliases": ["관리자별칭"],
        },
        headers={"X-API-Key": "test-admin-key"},
    )
    assert resp.status_code == 201


def test_agent_mapping_create_admin_key_succeeds(auth_client):
    resp = auth_client.post(
        "/api/v1/knowledge/agent-mappings",
        json={
            "agent_id": "LEADER_AGENT",
            "concept_id": "CONCEPT_CUSTOMER",
            "priority": 9,
        },
        headers={"X-API-Key": "test-admin-key"},
    )
    assert resp.status_code == 201
    mapping_id = resp.json()["id"]
    auth_client.delete(
        f"/api/v1/knowledge/agent-mappings/{mapping_id}",
        headers={"X-API-Key": "test-admin-key"},
    )


def test_alias_delete_admin_missing_row_returns_404(auth_client):
    resp = auth_client.delete(
        "/api/v1/knowledge/aliases/999999",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert resp.status_code == 404


def test_agent_catalog_create_analyst_key_returns_403(auth_client):
    resp = auth_client.post(
        "/api/v1/agents/catalog",
        json={
            "agent_id": f"AGENT_{uuid4().hex[:8]}",
            "name": "권한 테스트 Agent",
            "agent_type": "TEST",
            "description": "auth test",
            "capabilities": [],
            "is_active": True,
        },
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403


def test_tool_catalog_create_analyst_key_returns_403(auth_client):
    resp = auth_client.post(
        "/api/v1/tools/catalog",
        json={
            "api_id": f"API_{uuid4().hex[:8]}",
            "name": "권한 테스트 API",
            "endpoint": "http://example.test/api",
            "method": "GET",
            "description": "auth test",
            "is_active": True,
        },
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403


def test_chat_auth_disabled_no_key_succeeds(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        resp = client.post("/api/v1/ai/chat", json={"message": "신용대출 금리 알려줘"})
    app.dependency_overrides.clear()

    assert resp.status_code == 200
