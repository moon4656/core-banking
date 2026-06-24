from app.models.trace_model import DecisionTrace, TraceEvent
from app.services.trace_owner_backfill import backfill_trace_owners


def test_backfill_trace_owners_updates_missing_owner_from_request_event(db):
    trace = DecisionTrace(
        request_id="backfill-owner-001",
        session_id="backfill-session-001",
        owner_name=None,
        owner_role=None,
        user_query="신용대출 금리 알려줘",
        normalized_query="신용대출 금리 알려줘",
        request_meta={},
        memory_summary={},
        intent_analysis={},
        latency={},
        status="completed",
    )
    db.add(trace)
    db.add(
        TraceEvent(
            request_id="backfill-owner-001",
            event_type="REQUEST_RECEIVED",
            status="success",
            input_data={
                "message": "신용대출 금리 알려줘",
                "user_id": "legacy-user",
            },
        )
    )
    db.commit()

    result = backfill_trace_owners(db, dry_run=False)

    refreshed = (
        db.query(DecisionTrace)
        .filter(DecisionTrace.request_id == "backfill-owner-001")
        .first()
    )
    assert result.scanned >= 1
    assert result.updated >= 1
    assert refreshed is not None
    assert refreshed.owner_name == "legacy-user"
    assert refreshed.owner_role == "ANALYST"
    assert refreshed.request_meta["owner_name"] == "legacy-user"

    db.query(TraceEvent).filter(TraceEvent.request_id == "backfill-owner-001").delete()
    db.query(DecisionTrace).filter(DecisionTrace.request_id == "backfill-owner-001").delete()
    db.commit()
