from uuid import uuid4

import pytest

from app.models.memory_model import LongTermMemory
from app.models.trace_model import (
    AgentSelectionTrace,
    ConceptDetectionTrace,
    DecisionTrace,
    EvidenceReference,
    FinalAnswerTrace,
    LeaderDecision,
    LeaderDecisionEdge,
    LeaderDecisionNode,
    LeaderDecisionReview,
    RerankingTrace,
    ToolExecutionTrace,
    TraceEvent,
)


@pytest.fixture
def trace_scope_context(db):
    request_ids: list[str] = []
    session_ids: list[str] = []

    yield {"request_ids": request_ids, "session_ids": session_ids}

    if request_ids:
        for model in (
            LeaderDecisionReview,
            LeaderDecisionEdge,
            LeaderDecisionNode,
            FinalAnswerTrace,
            RerankingTrace,
            ToolExecutionTrace,
            AgentSelectionTrace,
            ConceptDetectionTrace,
            DecisionTrace,
            LeaderDecision,
            EvidenceReference,
            TraceEvent,
        ):
            db.query(model).filter(model.request_id.in_(request_ids)).delete(
                synchronize_session=False
            )

    if session_ids:
        db.query(LongTermMemory).filter(LongTermMemory.session_id.in_(session_ids)).delete(
            synchronize_session=False
        )

    db.commit()


def _login(auth_client, name: str, api_key: str) -> str:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"name": name, "apiKey": api_key},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _chat(auth_client, token: str, message: str, session_id: str) -> str:
    response = auth_client.post(
        "/api/v1/ai/chat",
        json={"message": message, "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["request_id"]


def test_trace_list_is_scoped_to_authenticated_owner(auth_client, trace_scope_context):
    owner_token = _login(auth_client, "alice", "test-analyst-key")
    other_token = _login(auth_client, "bob", "test-analyst-key")

    owner_session = f"scope-owner-{uuid4().hex[:8]}"
    other_session = f"scope-other-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].extend([owner_session, other_session])

    owner_request_id = _chat(
        auth_client,
        owner_token,
        "alice 요청: 신용대출 금리 알려줘",
        owner_session,
    )
    other_request_id = _chat(
        auth_client,
        other_token,
        "bob 요청: 우대금리 조건 알려줘",
        other_session,
    )
    trace_scope_context["request_ids"].extend([owner_request_id, other_request_id])

    response = auth_client.get(
        "/api/v1/ai/traces",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200, response.text
    request_ids = {item["request_id"] for item in response.json()}
    assert owner_request_id in request_ids
    assert other_request_id not in request_ids


def test_trace_detail_hides_other_users_request(auth_client, trace_scope_context):
    owner_token = _login(auth_client, "carol", "test-analyst-key")
    other_token = _login(auth_client, "dave", "test-analyst-key")

    owner_session = f"scope-detail-owner-{uuid4().hex[:8]}"
    other_session = f"scope-detail-other-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].extend([owner_session, other_session])

    owner_request_id = _chat(
        auth_client,
        owner_token,
        "carol 요청: 대출 필요서류 알려줘",
        owner_session,
    )
    other_request_id = _chat(
        auth_client,
        other_token,
        "dave 요청: 자동차담보대출 금리 알려줘",
        other_session,
    )
    trace_scope_context["request_ids"].extend([owner_request_id, other_request_id])

    response = auth_client.get(
        f"/api/v1/ai/traces/{other_request_id}/events",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404, response.text


def test_trace_list_admin_can_view_all_requests(auth_client, trace_scope_context):
    analyst_token = _login(auth_client, "erin", "test-analyst-key")
    admin_token = _login(auth_client, "ops-admin", "test-admin-key")

    analyst_session = f"scope-admin-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].append(analyst_session)

    analyst_request_id = _chat(
        auth_client,
        analyst_token,
        "erin 요청: 신용대출 금리와 서류 알려줘",
        analyst_session,
    )
    trace_scope_context["request_ids"].append(analyst_request_id)

    response = auth_client.get(
        "/api/v1/ai/traces",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    request_ids = {item["request_id"] for item in response.json()}
    assert analyst_request_id in request_ids


def test_decision_list_is_scoped_to_authenticated_owner(auth_client, trace_scope_context):
    owner_token = _login(auth_client, "frank", "test-analyst-key")
    other_token = _login(auth_client, "grace", "test-analyst-key")

    owner_session = f"scope-decision-owner-{uuid4().hex[:8]}"
    other_session = f"scope-decision-other-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].extend([owner_session, other_session])

    owner_request_id = _chat(
        auth_client,
        owner_token,
        "frank 요청: 신용대출 금리와 필요서류 알려줘",
        owner_session,
    )
    other_request_id = _chat(
        auth_client,
        other_token,
        "grace 요청: 우대금리와 정책 알려줘",
        other_session,
    )
    trace_scope_context["request_ids"].extend([owner_request_id, other_request_id])

    response = auth_client.get(
        "/api/v1/ai/decisions",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200, response.text
    request_ids = {item["request_id"] for item in response.json()["items"]}
    assert owner_request_id in request_ids
    assert other_request_id not in request_ids


def test_decision_graph_hides_other_users_request(auth_client, trace_scope_context):
    owner_token = _login(auth_client, "henry", "test-analyst-key")
    other_token = _login(auth_client, "irene", "test-analyst-key")

    owner_session = f"scope-graph-owner-{uuid4().hex[:8]}"
    other_session = f"scope-graph-other-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].extend([owner_session, other_session])

    owner_request_id = _chat(
        auth_client,
        owner_token,
        "henry 요청: 대출 금리 알려줘",
        owner_session,
    )
    other_request_id = _chat(
        auth_client,
        other_token,
        "irene 요청: 자동차담보대출 금리 알려줘",
        other_session,
    )
    trace_scope_context["request_ids"].extend([owner_request_id, other_request_id])

    response = auth_client.get(
        f"/api/v1/ai/decisions/{other_request_id}/graph",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404, response.text


def test_decision_admin_can_view_all_requests(auth_client, trace_scope_context):
    analyst_token = _login(auth_client, "julia", "test-analyst-key")
    admin_token = _login(auth_client, "ops-admin-2", "test-admin-key")

    analyst_session = f"scope-decision-admin-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].append(analyst_session)

    analyst_request_id = _chat(
        auth_client,
        analyst_token,
        "julia 요청: 대출 상품 알려줘",
        analyst_session,
    )
    trace_scope_context["request_ids"].append(analyst_request_id)

    response = auth_client.get(
        "/api/v1/ai/decisions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    request_ids = {item["request_id"] for item in response.json()["items"]}
    assert analyst_request_id in request_ids


def test_admin_can_reassign_trace_owner(auth_client, trace_scope_context):
    original_token = _login(auth_client, "kate", "test-analyst-key")
    reassigned_token = _login(auth_client, "legacy-fix-user", "test-analyst-key")
    admin_token = _login(auth_client, "ops-admin-3", "test-admin-key")

    session_id = f"scope-reassign-{uuid4().hex[:8]}"
    trace_scope_context["session_ids"].append(session_id)

    request_id = _chat(
        auth_client,
        original_token,
        "kate 요청: 신용대출 상품 알려줘",
        session_id,
    )
    trace_scope_context["request_ids"].append(request_id)

    update_response = auth_client.put(
        f"/api/v1/ai/traces/{request_id}/owner",
        json={"owner_name": "legacy-fix-user", "owner_role": "ANALYST"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["owner_name"] == "legacy-fix-user"

    original_list_response = auth_client.get(
        "/api/v1/ai/traces",
        headers={"Authorization": f"Bearer {original_token}"},
    )
    assert original_list_response.status_code == 200, original_list_response.text
    original_request_ids = {item["request_id"] for item in original_list_response.json()}
    assert request_id not in original_request_ids

    reassigned_list_response = auth_client.get(
        "/api/v1/ai/traces",
        headers={"Authorization": f"Bearer {reassigned_token}"},
    )
    assert reassigned_list_response.status_code == 200, reassigned_list_response.text
    reassigned_request_ids = {item["request_id"] for item in reassigned_list_response.json()}
    assert request_id in reassigned_request_ids
