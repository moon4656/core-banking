from uuid import uuid4

import pytest

from app.models.trace_model import EvidenceReference, TraceEvent


RATE_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uae08\ub9ac \uc54c\ub824\uc918"
RATE_AND_DOC_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uae08\ub9ac\uc640 \ud544\uc694 \uc11c\ub958 \uc54c\ub824\uc918"
APPLICATION_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uc2e0\uccad\ud558\ub824\uba74 \uc5b4\ub5a4 \uc11c\ub958\uac00 \ud544\uc694\ud558\uace0 \uc790\uaca9 \uc870\uac74\uc740 \ubb34\uc5c7\uc778\uac00\uc694?"
CREDIT_GRADE_MESSAGE = "\ub0b4 \uc2e0\uc6a9\ub4f1\uae09\uc774 \uc5b4\ub5bb\ud574?"
PRODUCT_MESSAGE = "\ub300\ucd9c \uc0c1\ud488 \uc885\ub958 \uc54c\ub824\uc918"
RATE_QUERY_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uae08\ub9ac \uc5bc\ub9c8\uc57c?"
COMPARISON_MESSAGE = "\uc9c1\uc7a5\uc778 \uc2e0\uc6a9\ub300\ucd9c\uacfc \uc804\uc138\uc790\uae08\ub300\ucd9c \uae08\ub9ac\ub97c \ube44\uad50\ud574\uc918"
UNKNOWN_MESSAGE = "\uc624\ub298 \uc810\uc2ec\uc774 \ubb50\uc57c?"
DISCLAIMER_SNIPPET = "\ucc38\uace0 \ubaa9\uc801"


@pytest.fixture(autouse=True)
def cleanup_test_traces(db):
    _delete_test_traces(db)
    yield
    _delete_test_traces(db)


def _delete_test_traces(db):
    db.query(EvidenceReference).filter(
        EvidenceReference.request_id.like("TEST-%")
    ).delete(synchronize_session=False)
    db.query(TraceEvent).filter(
        TraceEvent.request_id.like("TEST-%")
    ).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(autouse=True)
def cleanup_new_trace_rows(db):
    baseline = {
        "evidence_id": db.query(EvidenceReference.id)
        .order_by(EvidenceReference.id.desc())
        .limit(1)
        .scalar(),
        "trace_id": db.query(TraceEvent.id)
        .order_by(TraceEvent.id.desc())
        .limit(1)
        .scalar(),
    }
    yield

    evidence_query = db.query(EvidenceReference)
    trace_query = db.query(TraceEvent)

    if baseline["evidence_id"] is None:
        evidence_query.delete(synchronize_session=False)
    else:
        evidence_query.filter(
            EvidenceReference.id > baseline["evidence_id"]
        ).delete(synchronize_session=False)

    if baseline["trace_id"] is None:
        trace_query.delete(synchronize_session=False)
    else:
        trace_query.filter(
            TraceEvent.id > baseline["trace_id"]
        ).delete(synchronize_session=False)

    db.commit()


def test_chat_concept_detection(client):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_MESSAGE})

    assert resp.status_code == 200
    body = resp.json()
    detected = body["plan"]["detected_concepts"]
    loan_or_rate_concepts = {
        "CONCEPT_PERSONAL_CREDIT_LOAN",
        "CONCEPT_INTEREST_RATE",
        "CONCEPT_PREFERENTIAL_RATE",
        "CONCEPT_LOAN_PRODUCT",
    }
    assert any(c in loan_or_rate_concepts for c in detected), detected


def test_chat_trace_count(client):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_MESSAGE})

    assert resp.status_code == 200
    body = resp.json()
    assert body["trace_count"] >= 3


def test_chat_records_documented_trace_events(client, db):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_MESSAGE})

    assert resp.status_code == 200
    request_id = resp.json()["request_id"]
    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.request_id == request_id)
        .order_by(TraceEvent.id.asc())
        .all()
    )
    event_types = [event.event_type for event in events]

    assert "REQUEST_RECEIVED" in event_types
    assert "CONCEPT_DETECTED" in event_types
    assert "AGENT_SELECTED" in event_types
    assert "TOOL_INVOKED" in event_types
    assert "RESPONSE_COMPLETED" in event_types


def test_trace_list_returns_recent_request(client):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_MESSAGE})
    assert resp.status_code == 200
    request_id = resp.json()["request_id"]

    list_resp = client.get("/api/v1/ai/traces")
    assert list_resp.status_code == 200
    items = list_resp.json()

    matched = [item for item in items if item["request_id"] == request_id]
    assert matched
    assert matched[0]["event_count"] >= 1


def test_trace_list_includes_query_preview_and_pipeline_summary(client):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_AND_DOC_MESSAGE})
    assert resp.status_code == 200
    request_id = resp.json()["request_id"]

    list_resp = client.get("/api/v1/ai/traces")
    assert list_resp.status_code == 200
    items = list_resp.json()

    matched = next(item for item in items if item["request_id"] == request_id)
    assert matched["query_preview"] == RATE_AND_DOC_MESSAGE[:20]
    assert matched["intent"]
    assert isinstance(matched["selected_agents_count"], int)
    assert matched["selected_agents_count"] >= 1
    assert isinstance(matched["concept_count"], int)


def test_chat_evidence_count(client):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_MESSAGE})

    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence_count"] >= 1


def test_chat_answer_nonempty(client):
    resp = client.post("/api/v1/ai/chat", json={"message": RATE_MESSAGE})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] != ""
    assert len(body["answer"]) > 5


def test_chat_comparison_intent(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": COMPARISON_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    detected = body["plan"]["detected_concepts"]
    loan_rate_concepts = {
        "CONCEPT_PERSONAL_CREDIT_LOAN",
        "CONCEPT_LOAN_PRODUCT",
        "CONCEPT_INTEREST_RATE",
        "CONCEPT_PREFERENTIAL_RATE",
    }
    assert any(c in loan_rate_concepts for c in detected), detected
    assert len(body["results"]) >= 1
    assert body["answer"] != ""


def test_chat_credit_grade_query_prefers_personalized_rate_output(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": CREDIT_GRADE_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    result_api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_PERSONALIZED_RATE_LOOKUP" in result_api_ids, result_api_ids
    assert "\ub300\ucd9c \uc0c1\ud488" not in body["answer"]
    assert "\uc2e0\uc6a9\ub4f1\uae09" in body["answer"]


def test_chat_rate_query_does_not_return_product_section(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": RATE_QUERY_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    result_api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_RATE_LOOKUP" in result_api_ids, result_api_ids
    assert "\uae08\ub9ac" in body["answer"]
    assert "\ub300\ucd9c \uc0c1\ud488" not in body["answer"]


def test_chat_product_query_keeps_product_section(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": PRODUCT_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    result_api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_PRODUCT_LOOKUP" in result_api_ids, result_api_ids
    assert "\ub300\ucd9c \uc0c1\ud488" in body["answer"]


def test_chat_credit_grade_query_routes_rate_agent(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": CREDIT_GRADE_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "RATE_AGENT" in body["plan"]["routed_agents"]


def test_chat_credit_grade_query_plan_includes_personalized_rate_lookup(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": CREDIT_GRADE_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    step_api_ids = [step["api_id"] for step in body["plan"]["steps"]]
    assert "MOCK_PERSONALIZED_RATE_LOOKUP" in step_api_ids, step_api_ids


def test_chat_application_intent(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": APPLICATION_MESSAGE},
    )

    assert resp.status_code == 200
    body = resp.json()
    detected = body["plan"]["detected_concepts"]
    policy_doc_concepts = {
        "CONCEPT_REQUIRED_DOCUMENT",
        "CONCEPT_POLICY",
        "CONCEPT_TERMS",
        "CONCEPT_APPLICATION_CONDITION",
        "CONCEPT_PERSONAL_CREDIT_LOAN",
    }
    assert any(c in policy_doc_concepts for c in detected), detected
    assert len(body["results"]) >= 1

    eligibility_results = [
        r for r in body["results"] if r["api_id"] == "MOCK_ELIGIBILITY_CHECK"
    ]
    for result in eligibility_results:
        assert result["status"] == "success", result.get("error")


def test_chat_session_memory(client):
    session_id = f"test-session-memory-{uuid4().hex[:8]}"

    resp1 = client.post(
        "/api/v1/ai/chat",
        json={"message": RATE_MESSAGE, "session_id": session_id},
    )
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["memory_turns"] == 0

    resp2 = client.post(
        "/api/v1/ai/chat",
        json={"message": "\uc6b0\ub300\uae08\ub9ac \uc870\uac74\ub3c4 \uc54c\ub824\uc918", "session_id": session_id},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["memory_turns"] >= 1


def test_chat_compound_query_detects_multiple_concepts(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": RATE_AND_DOC_MESSAGE},
    )
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    rate_concepts = {"CONCEPT_INTEREST_RATE", "CONCEPT_PREFERENTIAL_RATE"}
    doc_concepts = {"CONCEPT_REQUIRED_DOCUMENT", "CONCEPT_POLICY", "CONCEPT_TERMS"}

    has_rate = any(c in rate_concepts for c in detected)
    has_doc = any(c in doc_concepts for c in detected)

    assert has_rate or has_doc, detected
    assert len(body["results"]) >= 1
    assert body["answer"]


def test_chat_compound_query_returns_decision_v2(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": RATE_AND_DOC_MESSAGE},
    )
    assert resp.status_code == 200
    decision = resp.json().get("decision_v2")

    assert decision is not None
    assert isinstance(decision.get("selected_agents"), list)
    assert isinstance(decision.get("rejected_agents"), list)
    assert decision.get("concepts") is not None


def test_chat_unknown_intent_returns_graceful_answer(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": UNKNOWN_MESSAGE},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["answer"]
    assert body["trace_count"] >= 1


def test_chat_validation_risk_flags_included_in_response(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": RATE_MESSAGE},
    )
    assert resp.status_code == 200
    decision = resp.json().get("decision_v2")

    assert decision is not None
    assert isinstance(decision.get("risk_flags"), list)
    assert "V010" in decision["risk_flags"]
    assert decision.get("requires_disclaimer") is True


def test_chat_disclaimer_appended_for_inquiry(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": RATE_MESSAGE},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert DISCLAIMER_SNIPPET in body["answer"]


