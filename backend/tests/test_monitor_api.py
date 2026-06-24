"""test_monitor_api.py — Leader Agent 모니터링 API 통합 테스트

엔드포인트:
  GET /api/v1/leader-agent/traces
  GET /api/v1/leader-agent/traces/{request_id}
  GET /api/v1/leader-agent/traces/{request_id}/gates

전제 조건:
  - alembic upgrade head (0014_add_monitor_tables 포함)
  - docker compose exec backend pytest tests/test_monitor_api.py -v
"""

from datetime import datetime
from uuid import uuid4

import pytest

from app.models.monitor_model import (
    MonAgentTrace,
    MonAnswerSentence,
    MonConceptDetection,
    MonGateCheck,
    MonIntentAnalysis,
    MonRoutingDecision,
    MonToolExecution,
)

# ── 픽스처 ────────────────────────────────────────────────────────────────

REQUEST_A = "TEST-API-MON-A001"
REQUEST_B = "TEST-API-MON-B001"
REQUEST_BLOCKED = "TEST-API-MON-BLOCKED"


def _login(auth_client, name: str, api_key: str) -> str:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"name": name, "apiKey": api_key},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def admin_headers(auth_client):
    token = _login(auth_client, "monitor-admin", "test-admin-key")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def seed_and_cleanup(db):
    """각 테스트 전 표준 데이터를 INSERT하고 후에 삭제한다."""
    _insert_full_trace(db, REQUEST_A, status="completed")
    _insert_full_trace(db, REQUEST_B, status="warning")
    _insert_blocked_trace(db, REQUEST_BLOCKED)
    yield
    for req in [REQUEST_A, REQUEST_B, REQUEST_BLOCKED]:
        _delete_trace(db, req)


def _delete_trace(db, request_id: str) -> None:
    for model in (
        MonGateCheck, MonAnswerSentence, MonToolExecution,
        MonRoutingDecision, MonConceptDetection, MonIntentAnalysis,
        MonAgentTrace,
    ):
        db.query(model).filter(model.request_id == request_id).delete()
    db.commit()


def _insert_full_trace(db, request_id: str, status: str = "completed") -> None:
    """7개 테이블에 완전한 트레이스 데이터를 삽입한다."""
    db.add(MonAgentTrace(
        request_id=request_id,
        user_id="user_test",
        session_id="sess_001",
        original_query="개인신용대출 금리 알려줘",
        normalized_query="개인신용대출 금리 조회",
        status=status,
        total_latency_ms=1250,
    ))
    db.add(MonIntentAnalysis(
        request_id=request_id,
        primary_intent="INQUIRY",
        secondary_intents=["interest_rate_lookup"],
        query_type="single_topic",
        needs_tool_execution=True,
        needs_memory=False,
        confidence=0.92,
        reason="금리 키워드 탐지",
    ))
    db.add(MonConceptDetection(
        request_id=request_id,
        source_text="금리",
        concept_id="CONCEPT_INTEREST_RATE",
        concept_label="Interest Rate",
        concept_type="rate",
        confidence=0.93,
        expanded_terms=["이자율"],
        status="normal",
    ))
    db.add(MonRoutingDecision(
        request_id=request_id,
        agent_name="RATE_AGENT",
        selected=True,
        related_concepts=["CONCEPT_INTEREST_RATE"],
        reason="금리 정보 조회 필요",
        routing_confidence=0.95,
        execution_order=1,
        status="selected",
    ))
    db.add(MonToolExecution(
        request_id=request_id,
        agent_name="RATE_AGENT",
        tool_name="MOCK_RATE_LOOKUP",
        tool_input={"concept_ids": ["CONCEPT_INTEREST_RATE"]},
        output_summary="금리: 4.2% ~ 9.8%",
        status="success",
        latency_ms=320,
        retry_count=0,
    ))
    db.add(MonAnswerSentence(
        request_id=request_id,
        answer_sentence="직장인 신용대출 금리는 연 4.2% ~ 9.8%입니다.",
        source_agent="RATE_AGENT",
        source_tool="MOCK_RATE_LOOKUP",
        evidence_summary="금리 조회 결과",
        grounded=True,
    ))
    for gate_name, gate_type, result, severity in [
        ("concept_confidence", "WARNING", "PASS",   "info"),
        ("agent_routing",      "BLOCK",   "PASS",   "critical"),
        ("answer_grounding",   "WARNING", "PASS",   "info"),
    ]:
        db.add(MonGateCheck(
            request_id=request_id,
            gate_name=gate_name,
            gate_type=gate_type,
            condition="auto",
            result=result,
            severity=severity,
            message=None,
        ))
    db.commit()


def _insert_blocked_trace(db, request_id: str) -> None:
    """Gate 2 BLOCKED 시나리오 데이터를 삽입한다."""
    db.add(MonAgentTrace(
        request_id=request_id,
        original_query="알 수 없는 질의",
        status="blocked",
        total_latency_ms=200,
    ))
    db.add(MonGateCheck(
        request_id=request_id,
        gate_name="agent_routing",
        gate_type="BLOCK",
        condition="selected_agents.length == 0",
        result="BLOCKED",
        severity="critical",
        message="선택된 Agent가 없습니다.",
    ))
    db.commit()


# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/leader-agent/traces
# ══════════════════════════════════════════════════════════════════════════

class TestListTraces:
    def test_returns_200_and_list(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "items" in body
        assert body["page"] == 1
        assert body["size"] == 20

    def test_items_contain_required_fields(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces", headers=admin_headers)
        items = resp.json()["items"]
        assert len(items) >= 1
        for item in items:
            assert "request_id" in item
            assert "status" in item

    def test_created_at_includes_utc_offset(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces", headers=admin_headers)
        item = resp.json()["items"][0]
        created_at = item["created_at"]
        assert created_at is not None
        assert created_at.endswith("+09:00")
        assert datetime.fromisoformat(created_at).tzinfo is not None

    def test_filter_by_status_completed(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces?status=completed", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["status"] == "completed" for i in items)

    def test_filter_by_status_blocked(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces?status=blocked", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["status"] == "blocked" for i in items)

    def test_pagination_size(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces?size=1&page=1", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1

    def test_pagination_page_2_may_be_empty(self, auth_client, admin_headers):
        """첫 페이지 total이 1 이하이면 2페이지는 빈 목록이어야 한다."""
        resp_p1 = auth_client.get("/api/v1/leader-agent/traces?size=100&page=1", headers=admin_headers)
        total = resp_p1.json()["total"]
        resp_p2 = auth_client.get("/api/v1/leader-agent/traces?size=100&page=2", headers=admin_headers)
        assert resp_p2.status_code == 200
        items_p2 = resp_p2.json()["items"]
        if total <= 100:
            assert len(items_p2) == 0

    def test_invalid_size_returns_422(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces?size=0", headers=admin_headers)
        assert resp.status_code == 422

    def test_invalid_page_returns_422(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces?page=0", headers=admin_headers)
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/leader-agent/traces/{request_id}
# ══════════════════════════════════════════════════════════════════════════

class TestGetTraceDetail:
    def test_returns_200_with_all_sections(self, auth_client, admin_headers):
        resp = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        for section in ["trace", "intent", "concepts", "routing", "tools", "sentences", "gates"]:
            assert section in body, f"섹션 누락: {section}"

    def test_trace_section_has_correct_fields(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        trace = body["trace"]
        assert trace["request_id"] == REQUEST_A
        assert trace["status"] == "completed"
        assert trace["total_latency_ms"] == 1250
        assert trace["original_query"] == "개인신용대출 금리 알려줘"
        assert trace["created_at"].endswith("+09:00")

    def test_intent_section_populated(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        intent = body["intent"]
        assert intent is not None
        assert intent["primary_intent"] == "INQUIRY"
        assert intent["needs_tool_execution"] is True
        assert "interest_rate_lookup" in intent["secondary_intents"]

    def test_concepts_section_populated(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        concepts = body["concepts"]
        assert len(concepts) >= 1
        c = concepts[0]
        assert c["concept_id"] == "CONCEPT_INTEREST_RATE"
        assert c["status"] == "normal"
        assert c["confidence"] == pytest.approx(0.93)

    def test_routing_section_selected_agent(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        routing = body["routing"]
        selected = [r for r in routing if r["selected"]]
        assert len(selected) >= 1
        assert selected[0]["agent_name"] == "RATE_AGENT"
        assert selected[0]["execution_order"] == 1

    def test_tools_section_populated(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        tools = body["tools"]
        assert len(tools) >= 1
        t = tools[0]
        assert t["tool_name"] == "MOCK_RATE_LOOKUP"
        assert t["status"] == "success"
        assert t["latency_ms"] == 320
        assert t["tool_input"] == {"concept_ids": ["CONCEPT_INTEREST_RATE"]}

    def test_sentences_section_all_grounded(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        sentences = body["sentences"]
        assert len(sentences) >= 1
        assert all(s["grounded"] for s in sentences)

    def test_gates_section_all_pass(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}", headers=admin_headers).json()
        gates = body["gates"]
        assert len(gates) == 3
        assert all(g["result"] == "PASS" for g in gates)

    def test_blocked_trace_shows_gate2_blocked(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_BLOCKED}", headers=admin_headers).json()
        gates = body["gates"]
        agent_routing_gate = next(
            (g for g in gates if g["gate_name"] == "agent_routing"), None
        )
        assert agent_routing_gate is not None
        assert agent_routing_gate["result"] == "BLOCKED"

    def test_not_found_returns_404(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces/NONEXISTENT-ID-99999", headers=admin_headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/leader-agent/traces/{request_id}/gates
# ══════════════════════════════════════════════════════════════════════════

class TestGetTraceGates:
    def test_returns_200_with_gates(self, auth_client, admin_headers):
        resp = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}/gates", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["request_id"] == REQUEST_A
        assert body["overall_status"] == "completed"
        assert len(body["gates"]) == 3

    def test_gate_fields_present(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}/gates", headers=admin_headers).json()
        for gate in body["gates"]:
            for field in ["gate_name", "gate_type", "result", "severity"]:
                assert field in gate

    def test_all_gates_pass_for_normal_trace(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_A}/gates", headers=admin_headers).json()
        assert all(g["result"] == "PASS" for g in body["gates"])

    def test_blocked_status_in_overall(self, auth_client, admin_headers):
        body = auth_client.get(f"/api/v1/leader-agent/traces/{REQUEST_BLOCKED}/gates", headers=admin_headers).json()
        assert body["overall_status"] == "blocked"
        gate2 = next(g for g in body["gates"] if g["gate_name"] == "agent_routing")
        assert gate2["result"] == "BLOCKED"

    def test_not_found_returns_404(self, auth_client, admin_headers):
        resp = auth_client.get("/api/v1/leader-agent/traces/NONEXISTENT-ID-99999/gates", headers=admin_headers)
        assert resp.status_code == 404


class TestMonitorScope:
    def test_non_admin_sees_only_owned_traces(self, auth_client, db):
        owned_request_id = f"TEST-API-MON-OWNED-{uuid4().hex[:6]}"
        other_request_id = f"TEST-API-MON-OTHER-{uuid4().hex[:6]}"
        _insert_full_trace(db, owned_request_id, status="completed")
        _insert_full_trace(db, other_request_id, status="completed")
        db.query(MonAgentTrace).filter(MonAgentTrace.request_id == owned_request_id).update(
            {"user_id": "user1"}, synchronize_session=False
        )
        db.query(MonAgentTrace).filter(MonAgentTrace.request_id == other_request_id).update(
            {"user_id": "other-user"}, synchronize_session=False
        )
        db.commit()

        token = _login(auth_client, "user1", "test-analyst-key")
        response = auth_client.get(
            "/api/v1/leader-agent/traces",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, response.text
        request_ids = {item["request_id"] for item in response.json()["items"]}
        assert owned_request_id in request_ids
        assert other_request_id not in request_ids

        _delete_trace(db, owned_request_id)
        _delete_trace(db, other_request_id)

    def test_non_admin_cannot_open_other_users_trace_detail(self, auth_client, db):
        request_id = f"TEST-API-MON-DENY-{uuid4().hex[:6]}"
        _insert_full_trace(db, request_id, status="completed")
        db.query(MonAgentTrace).filter(MonAgentTrace.request_id == request_id).update(
            {"user_id": "other-user"}, synchronize_session=False
        )
        db.commit()

        token = _login(auth_client, "user1", "test-analyst-key")
        response = auth_client.get(
            f"/api/v1/leader-agent/traces/{request_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404, response.text

        _delete_trace(db, request_id)
