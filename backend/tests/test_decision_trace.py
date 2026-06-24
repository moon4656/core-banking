import pytest
from app.models.trace_model import AgentSelectionTrace, TraceEvent


def test_decision_trace_detail_contains_mvp_fields(auth_client):
    chat_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "신용대출 금리와 필요서류 알려줘", "session_id": "trace-mvp-001"},
    )
    assert chat_resp.status_code == 200
    request_id = chat_resp.json()["request_id"]

    trace_resp = auth_client.get(
        f"/api/v1/ai/decisions/{request_id}/trace",
        headers={"X-API-Key": "test-readonly-key"},
    )

    assert trace_resp.status_code == 200
    payload = trace_resp.json()
    assert payload["request_id"] == request_id
    assert payload["user_query"]
    assert payload["intent_analysis"]["intent"]
    assert isinstance(payload["concepts"], list)
    assert "selected_agents" in payload["agent_selection"]
    assert "rejected_agents" in payload["agent_selection"]
    assert isinstance(payload["tool_executions"], list)
    assert "final_answer" in payload
    assert "latency" in payload


def test_decision_trace_includes_memory_items_and_leader_decision(auth_client):
    session_id = "trace-memory-detail-001"

    first_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "신용대출 금리 알려줘", "session_id": session_id},
    )
    assert first_resp.status_code == 200

    second_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "그럼 필요서류도 알려줘", "session_id": session_id},
    )
    assert second_resp.status_code == 200
    request_id = second_resp.json()["request_id"]

    trace_resp = auth_client.get(
        f"/api/v1/ai/decisions/{request_id}/trace",
        headers={"X-API-Key": "test-readonly-key"},
    )

    assert trace_resp.status_code == 200
    payload = trace_resp.json()
    assert "items" in payload["memory"]["short_memory"]
    assert isinstance(payload["memory"]["short_memory"]["items"], list)
    assert "items" in payload["memory"]["long_term_memory"]
    assert isinstance(payload["memory"]["long_term_memory"]["items"], list)
    assert "leader_decision" in payload
    assert payload["leader_decision"]["description"]
    assert isinstance(payload["leader_decision"]["selected_agents"], list)
    assert isinstance(payload["leader_decision"]["rejected_agents"], list)


def test_chat_persists_sub_agent_selection_reasons(auth_client, db):
    chat_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "신용대출 금리 알려줘", "session_id": "trace-mvp-002"},
    )
    assert chat_resp.status_code == 200
    request_id = chat_resp.json()["request_id"]

    rows = (
        db.query(AgentSelectionTrace)
        .filter(AgentSelectionTrace.request_id == request_id)
        .all()
    )

    assert rows
    assert all(row.agent_id != "LEADER_AGENT" for row in rows)
    assert any(row.selected is True for row in rows)
    assert all(row.reason for row in rows)


def test_chat_persists_memory_save_events_and_graph_nodes(auth_client, db):
    chat_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "대출 금리와 서류 알려줘", "session_id": "trace-memory-save-001"},
    )
    assert chat_resp.status_code == 200
    request_id = chat_resp.json()["request_id"]

    event_types = [
        row.event_type
        for row in db.query(TraceEvent).filter(TraceEvent.request_id == request_id).all()
    ]
    assert "MEMORY_SAVED" in event_types
    assert "LTM_SAVED" in event_types

    graph_resp = auth_client.get(
        f"/api/v1/ai/decisions/{request_id}/graph",
        headers={"X-API-Key": "test-readonly-key"},
    )
    assert graph_resp.status_code == 200
    payload = graph_resp.json()
    memory_write_nodes = [node for node in payload["nodes"] if node["node_type"] == "MEMORY_WRITE"]
    assert len(memory_write_nodes) >= 2


# ── Phase 3 테스트 ─────────────────────────────────────────────────────────────

def test_search_agent_always_rejected_without_counseling_keywords(auth_client, db):
    """상담이력 키워드 없는 일반 금리 질문 → SEARCH_AGENT는 반드시 selected=False 로 기록돼야 한다."""
    chat_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "신용대출 금리 알려줘", "session_id": "p3-search-reject-001"},
    )
    assert chat_resp.status_code == 200
    request_id = chat_resp.json()["request_id"]

    rows = (
        db.query(AgentSelectionTrace)
        .filter(AgentSelectionTrace.request_id == request_id)
        .all()
    )
    agent_ids = {r.agent_id for r in rows}

    # 4개 Sub-Agent 모두 레코드가 있어야 한다
    assert "SEARCH_AGENT" in agent_ids, f"SEARCH_AGENT 레코드 없음. 존재하는 Agent: {agent_ids}"
    assert "RATE_AGENT" in agent_ids
    assert "PRODUCT_AGENT" in agent_ids
    assert "POLICY_AGENT" in agent_ids

    search_row = next(r for r in rows if r.agent_id == "SEARCH_AGENT")
    assert search_row.selected is False, "SEARCH_AGENT는 미선택이어야 함"
    assert search_row.rejection_reason, "SEARCH_AGENT rejection_reason이 비어 있음"
    # v2 rejection reason에 '상담이력' 또는 '키워드' 관련 문구가 포함돼야 한다
    assert any(
        kw in search_row.rejection_reason
        for kw in ["상담이력", "키워드", "POLICY_AGENT", "미감지"]
    ), f"예상 문구 없음: {search_row.rejection_reason}"


def test_selected_agents_persist_role_and_execution_mode(auth_client, db):
    """금리+서류 질문 → RATE_AGENT/POLICY_AGENT에 role·execution_mode·tools_assigned 가 저장돼야 한다."""
    chat_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "대출 금리와 필요서류 알려줘", "session_id": "p3-role-mode-001"},
    )
    assert chat_resp.status_code == 200
    request_id = chat_resp.json()["request_id"]

    rows = (
        db.query(AgentSelectionTrace)
        .filter(AgentSelectionTrace.request_id == request_id)
        .all()
    )
    row_map = {r.agent_id: r for r in rows}

    # RATE_AGENT: selected=True, role/execution_mode 저장
    rate_row = row_map.get("RATE_AGENT")
    assert rate_row is not None, "RATE_AGENT 레코드 없음"
    assert rate_row.selected is True
    assert rate_row.role == "rate_lookup", f"RATE_AGENT role: {rate_row.role}"
    assert rate_row.execution_mode == "normal", f"RATE_AGENT execution_mode: {rate_row.execution_mode}"
    assert isinstance(rate_row.tools_assigned, list) and len(rate_row.tools_assigned) > 0
    assert isinstance(rate_row.decision_rule_ids, list) and len(rate_row.decision_rule_ids) > 0

    # PRODUCT_AGENT: execution_mode=lightweight
    product_row = row_map.get("PRODUCT_AGENT")
    assert product_row is not None, "PRODUCT_AGENT 레코드 없음"
    assert product_row.selected is True
    assert product_row.execution_mode == "lightweight", f"PRODUCT_AGENT execution_mode: {product_row.execution_mode}"

    # SEARCH_AGENT: role/execution_mode/tools_assigned 는 None/빈 리스트여야 한다
    search_row = row_map.get("SEARCH_AGENT")
    assert search_row is not None, "SEARCH_AGENT 레코드 없음"
    assert search_row.selected is False
    assert search_row.role is None
    assert search_row.execution_mode is None
    assert search_row.tools_assigned == []
