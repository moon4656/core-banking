def test_agent_catalog_create_update_delete(client):
    agent_id = "TEST_AGENT_ADMIN"

    create_resp = client.post(
        "/api/v1/agents/catalog",
        json={
            "agent_id": agent_id,
            "name": "테스트 운영 Agent",
            "agent_type": "TEST",
            "description": "catalog test",
            "capabilities": ["demo"],
            "is_active": True,
        },
    )
    assert create_resp.status_code == 201, create_resp.text

    update_resp = client.put(
        f"/api/v1/agents/catalog/{agent_id}",
        json={
            "name": "테스트 운영 Agent 수정",
            "agent_type": "OPS",
            "description": "catalog update",
            "capabilities": ["demo", "update"],
            "is_active": False,
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["agent_type"] == "OPS"
    assert updated["is_active"] is False

    delete_resp = client.delete(f"/api/v1/agents/catalog/{agent_id}")
    assert delete_resp.status_code == 204, delete_resp.text


def test_tool_catalog_create_update_delete(client):
    api_id = "TEST_API_ADMIN"

    create_resp = client.post(
        "/api/v1/tools/catalog",
        json={
            "api_id": api_id,
            "name": "테스트 운영 API",
            "endpoint": "http://example.test/mock",
            "method": "GET",
            "description": "catalog test",
            "is_active": True,
        },
    )
    assert create_resp.status_code == 201, create_resp.text

    update_resp = client.put(
        f"/api/v1/tools/catalog/{api_id}",
        json={
            "name": "테스트 운영 API 수정",
            "endpoint": "http://example.test/mock/v2",
            "method": "POST",
            "description": "catalog update",
            "is_active": False,
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["method"] == "POST"
    assert updated["is_active"] is False

    delete_resp = client.delete(f"/api/v1/tools/catalog/{api_id}")
    assert delete_resp.status_code == 204, delete_resp.text
