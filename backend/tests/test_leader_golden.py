from uuid import uuid4


PRODUCT_MESSAGE = "\ub300\ucd9c \uc0c1\ud488 \uc885\ub958 \uc54c\ub824\uc918"
RATE_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uae08\ub9ac \uc5bc\ub9c8\uc57c?"
CREDIT_GRADE_MESSAGE = "\ub0b4 \uc2e0\uc6a9\ub4f1\uae09\uc774 \uc5b4\ub5bb\ud574?"
COMPOUND_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uae08\ub9ac\uc640 \ud544\uc694 \uc11c\ub958 \uc54c\ub824\uc918"
APPLICATION_MESSAGE = "\uc2e0\uc6a9\ub300\ucd9c \uc2e0\uccad\ud558\ub824\uba74 \uc5b4\ub5a4 \uc11c\ub958\uac00 \ud544\uc694\ud574?"
CLARIFICATION_MESSAGE = "\ub300\ucd9c \uc2e0\uccad\ud558\ub824\uba74?"


def _post_chat(client, message: str, session_id: str | None = None) -> dict:
    payload = {"message": message}
    if session_id is not None:
        payload["session_id"] = session_id
    response = client.post("/api/v1/ai/chat", json=payload)
    assert response.status_code == 200
    return response.json()


def _step_api_ids(body: dict) -> list[str]:
    return [step["api_id"] for step in body["plan"]["steps"]]


def test_leader_golden_product_query(client):
    body = _post_chat(
        client,
        PRODUCT_MESSAGE,
        session_id=f"golden-{uuid4().hex[:8]}",
    )

    assert "CONCEPT_LOAN_PRODUCT" in body["plan"]["detected_concepts"]
    assert "PRODUCT_AGENT" in body["plan"]["routed_agents"]
    assert "MOCK_PRODUCT_LOOKUP" in _step_api_ids(body)
    assert body["answer"]


def test_leader_golden_rate_query(client):
    body = _post_chat(
        client,
        RATE_MESSAGE,
        session_id=f"golden-{uuid4().hex[:8]}",
    )

    assert "CONCEPT_INTEREST_RATE" in body["plan"]["detected_concepts"]
    assert "RATE_AGENT" in body["plan"]["routed_agents"]
    assert "MOCK_RATE_LOOKUP" in _step_api_ids(body)
    assert body["results"]


def test_leader_golden_credit_grade_query_detects_rate_concept(client):
    body = _post_chat(
        client,
        CREDIT_GRADE_MESSAGE,
        session_id=f"golden-{uuid4().hex[:8]}",
    )

    assert "CONCEPT_INTEREST_RATE" in body["plan"]["detected_concepts"]


def test_leader_golden_compound_query(client):
    body = _post_chat(
        client,
        COMPOUND_MESSAGE,
        session_id=f"golden-{uuid4().hex[:8]}",
    )

    detected = set(body["plan"]["detected_concepts"])
    assert "CONCEPT_INTEREST_RATE" in detected
    assert (
        "CONCEPT_REQUIRED_DOCUMENT" in detected
        or "CONCEPT_POLICY" in detected
        or "CONCEPT_TERMS" in detected
    )
    assert "MOCK_RATE_LOOKUP" in _step_api_ids(body)
    assert any(
        api_id in _step_api_ids(body)
        for api_id in ("MOCK_POLICY_LOOKUP", "MOCK_DOCUMENT_SEARCH", "MOCK_ELIGIBILITY_CHECK")
    )


def test_leader_golden_application_query(client):
    body = _post_chat(
        client,
        APPLICATION_MESSAGE,
        session_id=f"golden-{uuid4().hex[:8]}",
    )

    detected = set(body["plan"]["detected_concepts"])
    assert "CONCEPT_PERSONAL_CREDIT_LOAN" in detected or "CONCEPT_LOAN_PRODUCT" in detected
    assert (
        "CONCEPT_REQUIRED_DOCUMENT" in detected
        or "CONCEPT_APPLICATION_CONDITION" in detected
        or "CONCEPT_POLICY" in detected
    )
    assert body["answer"]

    if body.get("needs_clarification"):
        assert body["clarification_question"]
        assert body["plan"]["steps"] == []
    else:
        assert any(
            api_id in _step_api_ids(body)
            for api_id in ("MOCK_POLICY_LOOKUP", "MOCK_DOCUMENT_SEARCH", "MOCK_ELIGIBILITY_CHECK")
        )


def test_leader_golden_clarification_query(client):
    body = _post_chat(
        client,
        CLARIFICATION_MESSAGE,
        session_id=f"golden-{uuid4().hex[:8]}",
    )

    assert "needs_clarification" in body
    assert isinstance(body["needs_clarification"], bool)
    if body["needs_clarification"]:
        assert body["clarification_question"]

