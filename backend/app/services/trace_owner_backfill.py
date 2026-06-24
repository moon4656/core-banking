from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.trace_model import DecisionTrace, TraceEvent


@dataclass
class TraceOwnerBackfillResult:
    scanned: int
    updated: int
    skipped: int


def _extract_owner_name(event: TraceEvent | None) -> str | None:
    if event is None or not event.input_data:
        return None

    input_data = event.input_data
    owner_name = input_data.get("user_id") or input_data.get("client_user_id")
    if not owner_name:
        return None
    return str(owner_name).strip() or None


def backfill_trace_owners(
    db: Session,
    *,
    dry_run: bool = True,
    limit: int | None = None,
) -> TraceOwnerBackfillResult:
    query = (
        db.query(DecisionTrace)
        .filter(DecisionTrace.owner_name.is_(None))
        .order_by(DecisionTrace.created_at.asc(), DecisionTrace.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)

    traces = query.all()

    updated = 0
    skipped = 0

    for trace in traces:
        request_event = (
            db.query(TraceEvent)
            .filter(
                TraceEvent.request_id == trace.request_id,
                TraceEvent.event_type == "REQUEST_RECEIVED",
            )
            .order_by(TraceEvent.id.asc())
            .first()
        )

        owner_name = _extract_owner_name(request_event)
        if owner_name is None:
            skipped += 1
            continue

        updated += 1
        if dry_run:
            continue

        trace.owner_name = owner_name
        trace.owner_role = trace.owner_role or "ANALYST"

        request_meta = dict(trace.request_meta or {})
        request_meta.setdefault("owner_name", owner_name)
        request_meta.setdefault("owner_role", trace.owner_role)
        trace.request_meta = request_meta

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return TraceOwnerBackfillResult(
        scanned=len(traces),
        updated=updated,
        skipped=skipped,
    )
