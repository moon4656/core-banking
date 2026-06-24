from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import AuthContext, Role, require_admin, require_readonly_context
from app.models.trace_model import DecisionTrace, EvidenceReference, LeaderDecision, TraceEvent

router = APIRouter(prefix="/api/v1/ai", tags=["trace"])


class TraceEventResponse(BaseModel):
    id: int
    event_type: str
    agent_id: str | None
    tool_id: str | None
    status: str
    input_data: dict | None
    output_data: dict | None
    duration_ms: int | None
    created_at: str

    class Config:
        from_attributes = True


class EvidenceResponse(BaseModel):
    id: int
    concept_id: str | None
    source_id: str | None
    confidence_score: float | None
    data_quality_score: float | None
    intent_relevance_score: float | None
    response_latency_ms: int | None
    item_count: int | None
    quality_flags: dict | None
    related_evidence_ids: list[int] | None
    created_at: str

    class Config:
        from_attributes = True


class TraceSummaryResponse(BaseModel):
    request_id: str
    owner_name: str | None = None
    owner_role: str | None = None
    event_count: int
    evidence_count: int
    avg_confidence: float | None
    avg_data_quality: float | None
    avg_intent_relevance: float | None
    linked_evidence_count: int
    events_by_type: dict[str, int]


class TraceListItemResponse(BaseModel):
    request_id: str
    owner_name: str | None = None
    owner_role: str | None = None
    first_event_at: str
    last_event_at: str
    event_count: int
    evidence_count: int
    last_event_type: str
    query_preview: str | None = None
    intent: str | None = None
    selected_agents_count: int = 0
    concept_count: int = 0


class TraceOwnerUpdateRequest(BaseModel):
    owner_name: str
    owner_role: str | None = "ANALYST"


class TraceOwnerUpdateResponse(BaseModel):
    request_id: str
    owner_name: str
    owner_role: str | None


def _avg(values: list[float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    return round(sum(filtered) / len(filtered), 4) if filtered else None


def _build_trace_summary(
    trace: DecisionTrace | None,
    request_id: str,
    events: list[TraceEvent],
    evidences: list[EvidenceReference],
) -> TraceSummaryResponse:
    events_by_type: dict[str, int] = {}
    for event in events:
        events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1

    return TraceSummaryResponse(
        request_id=request_id,
        owner_name=trace.owner_name if trace else None,
        owner_role=trace.owner_role if trace else None,
        event_count=len(events),
        evidence_count=len(evidences),
        avg_confidence=_avg([ev.confidence_score for ev in evidences]),
        avg_data_quality=_avg([ev.data_quality_score for ev in evidences]),
        avg_intent_relevance=_avg([ev.intent_relevance_score for ev in evidences]),
        linked_evidence_count=sum(1 for ev in evidences if ev.related_evidence_ids),
        events_by_type=events_by_type,
    )


def _apply_trace_scope(query, auth: AuthContext, db: Session):
    if auth.role == Role.ADMIN:
        return query

    owned_request_ids = (
        select(DecisionTrace.request_id).where(DecisionTrace.owner_name == auth.name)
    )
    return query.filter(TraceEvent.request_id.in_(owned_request_ids))


def _ensure_trace_access(db: Session, auth: AuthContext, request_id: str) -> None:
    if auth.role == Role.ADMIN:
        return

    owned_trace = (
        db.query(DecisionTrace.id)
        .filter(
            DecisionTrace.request_id == request_id,
            DecisionTrace.owner_name == auth.name,
        )
        .first()
    )
    if owned_trace is None:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' not found")


@router.get("/traces", response_model=list[TraceListItemResponse])
def list_traces(
    limit: int = Query(20, ge=1, le=100),
    request_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    query = db.query(TraceEvent)
    query = _apply_trace_scope(query, auth, db)

    if request_id:
        query = query.filter(TraceEvent.request_id.contains(request_id))
    if event_type:
        query = query.filter(TraceEvent.event_type == event_type)

    events = query.order_by(TraceEvent.created_at.desc(), TraceEvent.id.desc()).all()
    grouped: dict[str, list[TraceEvent]] = {}
    for event in events:
        grouped.setdefault(event.request_id, []).append(event)

    items: list[TraceListItemResponse] = []
    for current_request_id, request_events in grouped.items():
        ordered = sorted(request_events, key=lambda item: (item.created_at, item.id))
        evidence_count = (
            db.query(EvidenceReference)
            .filter(EvidenceReference.request_id == current_request_id)
            .count()
        )
        trace = (
            db.query(DecisionTrace)
            .filter(DecisionTrace.request_id == current_request_id)
            .first()
        )
        leader_decision = (
            db.query(LeaderDecision)
            .filter(LeaderDecision.request_id == current_request_id)
            .first()
        )
        query_preview = None
        if trace and trace.user_query:
            query_preview = trace.user_query[:20]
        elif ordered[0].input_data:
            query_preview = str(ordered[0].input_data.get("message", ""))[:20] or None

        items.append(
            TraceListItemResponse(
                request_id=current_request_id,
                owner_name=trace.owner_name if trace else None,
                owner_role=trace.owner_role if trace else None,
                first_event_at=str(ordered[0].created_at),
                last_event_at=str(ordered[-1].created_at),
                event_count=len(ordered),
                evidence_count=evidence_count,
                last_event_type=ordered[-1].event_type,
                query_preview=query_preview,
                intent=leader_decision.detected_intent if leader_decision else None,
                selected_agents_count=len(leader_decision.selected_agents or []) if leader_decision else 0,
                concept_count=len(leader_decision.detected_concepts or []) if leader_decision else 0,
            )
        )

    items.sort(key=lambda item: item.last_event_at, reverse=True)
    return items[:limit]


@router.get("/traces/{request_id}", response_model=TraceSummaryResponse)
def get_trace_summary(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    _ensure_trace_access(db, auth, request_id)

    events = db.query(TraceEvent).filter(TraceEvent.request_id == request_id).all()
    evidences = db.query(EvidenceReference).filter(EvidenceReference.request_id == request_id).all()
    trace = db.query(DecisionTrace).filter(DecisionTrace.request_id == request_id).first()

    if not events and not evidences:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' not found")

    return _build_trace_summary(trace, request_id, events, evidences)


@router.get("/traces/{request_id}/events", response_model=list[TraceEventResponse])
def get_trace_events(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    _ensure_trace_access(db, auth, request_id)

    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.request_id == request_id)
        .order_by(TraceEvent.id.asc())
        .all()
    )
    if not events:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' has no events")

    return [
        TraceEventResponse(
            id=event.id,
            event_type=event.event_type,
            agent_id=event.agent_id,
            tool_id=event.tool_id,
            status=event.status,
            input_data=event.input_data,
            output_data=event.output_data,
            duration_ms=event.duration_ms,
            created_at=str(event.created_at),
        )
        for event in events
    ]


@router.get("/traces/{request_id}/evidence", response_model=list[EvidenceResponse])
def get_trace_evidence(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    _ensure_trace_access(db, auth, request_id)

    evidences = (
        db.query(EvidenceReference)
        .filter(EvidenceReference.request_id == request_id)
        .order_by(EvidenceReference.confidence_score.desc().nullslast())
        .all()
    )
    if not evidences:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' has no evidence")

    return [
        EvidenceResponse(
            id=ev.id,
            concept_id=ev.concept_id,
            source_id=ev.source_id,
            confidence_score=ev.confidence_score,
            data_quality_score=ev.data_quality_score,
            intent_relevance_score=ev.intent_relevance_score,
            response_latency_ms=ev.response_latency_ms,
            item_count=ev.item_count,
            quality_flags=ev.quality_flags,
            related_evidence_ids=ev.related_evidence_ids,
            created_at=str(ev.created_at),
        )
        for ev in evidences
    ]


@router.put("/traces/{request_id}/owner", response_model=TraceOwnerUpdateResponse)
def update_trace_owner(
    request_id: str,
    body: TraceOwnerUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    trace = db.query(DecisionTrace).filter(DecisionTrace.request_id == request_id).first()
    if trace is None:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' not found")

    owner_name = body.owner_name.strip()
    if not owner_name:
        raise HTTPException(status_code=400, detail="owner_name is required")

    trace.owner_name = owner_name
    trace.owner_role = body.owner_role

    request_meta = dict(trace.request_meta or {})
    request_meta["owner_name"] = owner_name
    request_meta["owner_role"] = body.owner_role
    trace.request_meta = request_meta

    db.commit()

    return TraceOwnerUpdateResponse(
        request_id=request_id,
        owner_name=owner_name,
        owner_role=body.owner_role,
    )
