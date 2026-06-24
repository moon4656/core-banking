from app.models.trace_model import EvidenceReference, LeaderDecision, TraceEvent


def _delete_new_rows(db, baseline: dict[str, int | None]):
    evidence_query = db.query(EvidenceReference)
    trace_query = db.query(TraceEvent)
    decision_query = db.query(LeaderDecision)

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

    if baseline["decision_id"] is None:
        decision_query.delete(synchronize_session=False)
    else:
        decision_query.filter(
            LeaderDecision.id > baseline["decision_id"]
        ).delete(synchronize_session=False)

    db.commit()


def _baseline_ids(db) -> dict[str, int | None]:
    return {
        "evidence_id": db.query(EvidenceReference.id)
        .order_by(EvidenceReference.id.desc())
        .limit(1)
        .scalar(),
        "trace_id": db.query(TraceEvent.id)
        .order_by(TraceEvent.id.desc())
        .limit(1)
        .scalar(),
        "decision_id": db.query(LeaderDecision.id)
        .order_by(LeaderDecision.id.desc())
        .limit(1)
        .scalar(),
    }


def test_leader_evaluation_list_admin_key_succeeds(auth_client, db):
    baseline = _baseline_ids(db)
    try:
        chat_resp = auth_client.post(
            "/api/v1/ai/chat",
            json={"message": "신용대출 금리와 필요서류 알려줘"},
            headers={"X-API-Key": "test-admin-key"},
        )
        assert chat_resp.status_code == 200
        request_id = chat_resp.json()["request_id"]

        resp = auth_client.get(
            "/api/v1/admin/leader-evaluations",
            headers={"X-API-Key": "test-admin-key"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

        matched = [item for item in body["items"] if item["request_id"] == request_id]
        assert matched, f"leader evaluation list does not contain request_id={request_id}"
        assert matched[0]["user_question"] == "신용대출 금리와 필요서류 알려줘"
    finally:
        _delete_new_rows(db, baseline)


def test_leader_evaluation_detail_admin_key_succeeds(auth_client, db):
    baseline = _baseline_ids(db)
    try:
        chat_resp = auth_client.post(
            "/api/v1/ai/chat",
            json={"message": "신용대출 금리 알려줘"},
            headers={"X-API-Key": "test-admin-key"},
        )
        assert chat_resp.status_code == 200
        request_id = chat_resp.json()["request_id"]

        resp = auth_client.get(
            f"/api/v1/admin/leader-evaluations/{request_id}",
            headers={"X-API-Key": "test-admin-key"},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert body["request_id"] == request_id
        assert body["user_question"] == "신용대출 금리 알려줘"
        assert "leader_decision" in body
        assert "evidence_summary" in body
        assert len(body["trace_events"]) >= 1
    finally:
        _delete_new_rows(db, baseline)


def test_leader_evaluation_analyst_key_returns_403(auth_client):
    resp = auth_client.get(
        "/api/v1/admin/leader-evaluations",
        headers={"X-API-Key": "test-analyst-key"},
    )
    assert resp.status_code == 403
