from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Role, require_admin
from app.models.trace_model import EvidenceReference, LeaderDecision, TraceEvent
from app.schemas.leader_evaluation import (
    EvidenceSummaryResponse,
    LeaderDecisionResponse,
    LeaderEvaluationDetailResponse,
    LeaderEvaluationEvidenceResponse,
    LeaderEvaluationListItemResponse,
    LeaderEvaluationListResponse,
    LeaderEvaluationReviewResponse,
    LeaderEvaluationTraceEventResponse,
    ScoreBreakdown,
)

router = APIRouter(prefix="/api/v1/admin", tags=["leader-evaluation"])


def _avg(values: list[float | None]) -> float | None:
    filtered = [v for v in values if v is not None]
    return round(sum(filtered) / len(filtered), 4) if filtered else None


def _find_first_event(events: list[TraceEvent], event_type: str) -> TraceEvent | None:
    for event in events:
        if event.event_type == event_type:
            return event
    return None


def _extract_unrouted_concepts(events: list[TraceEvent]) -> list[str]:
    event = _find_first_event(events, "AGENT_SELECTED")
    if event and event.output_data:
        return list(event.output_data.get("unrouted_concepts", []))
    return []


def _compute_score_breakdown(
    decision: LeaderDecision | None,
    evidences: list[EvidenceReference],
    unrouted_concepts: list[str],
    all_concepts: list[str],
) -> ScoreBreakdown:
    intent = decision.detected_intent if decision else None
    intent_score = 1.0 if (intent and intent not in [None, "OTHER"]) else 0.5

    total_c = len(all_concepts)
    unrouted_c = len(unrouted_concepts)
    concept_score = 1.0 if total_c == 0 else round((total_c - unrouted_c) / total_c, 4)
    routing_score = concept_score

    tool_success_score = decision.confidence_score if decision else None
    evidence_score = _avg([ev.confidence_score for ev in evidences])

    if all(v is not None for v in [intent_score, concept_score, routing_score, tool_success_score, evidence_score]):
        final_score = round(
            intent_score * 0.15
            + concept_score * 0.20
            + routing_score * 0.15
            + tool_success_score * 0.25  # type: ignore[operator]
            + evidence_score * 0.25,  # type: ignore[operator]
            4,
        )
    else:
        final_score = tool_success_score

    return ScoreBreakdown(
        intent_score=intent_score,
        concept_score=concept_score,
        routing_score=routing_score,
        tool_success_score=tool_success_score,
        evidence_score=evidence_score,
        final_score=final_score,
    )


def _infer_review_reason(
    decision: LeaderDecision | None,
    evidences: list[EvidenceReference],
    failed_step_count: int,
    unrouted_concepts: list[str],
    events: list[TraceEvent],
    missing_concepts: list[str] | None = None,
) -> str | None:
    # 시스템 오류 감지: TraceEvent 자체가 없거나 REQUEST_RECEIVED만 있는 경우
    non_request_events = [e for e in events if e.event_type not in ("REQUEST_RECEIVED", "RESPONSE_COMPLETED")]
    if not non_request_events and not decision:
        return "BLOCKED"

    if failed_step_count > 0 and not evidences:
        return "TOOL_FAILED"
    if not evidences and decision:
        return "NO_EVIDENCE"
    if decision and (not decision.detected_concepts or len(decision.detected_concepts) == 0):
        return "NO_CONCEPT_DETECTED"
    if unrouted_concepts:
        return "UNROUTED_CONCEPTS"

    # 직접 탐지된 concept 중 근거가 없는 항목 존재 → 커버리지 미흡
    if missing_concepts:
        direct = list(decision.direct_concepts or []) if decision else []
        if any(c in direct for c in missing_concepts):
            return "MISSING_DIRECT_EVIDENCE"

    avg_conf = _avg([ev.confidence_score for ev in evidences])
    if avg_conf is not None and avg_conf < 0.60:
        return "LOW_EVIDENCE_QUALITY"
    if decision and decision.confidence_score is not None and decision.confidence_score < 0.5:
        return "LOW_LEADER_CONFIDENCE"

    return None


def _infer_overall_result(
    decision: LeaderDecision | None,
    evidences: list[EvidenceReference],
    avg_evidence_confidence: float | None,
    failed_step_count: int,
    events: list[TraceEvent],
    missing_concepts: list[str] | None = None,
) -> str | None:
    # BLOCKED: 시스템 오류로 처리 자체가 불완전한 경우
    non_request_events = [e for e in events if e.event_type not in ("REQUEST_RECEIVED", "RESPONSE_COMPLETED")]
    if not non_request_events and not decision:
        return "BLOCKED"

    leader_confidence = decision.confidence_score if decision else None
    if leader_confidence is None and avg_evidence_confidence is None:
        return None

    # FAIL 조건
    if failed_step_count > 0 or (leader_confidence is not None and leader_confidence < 0.5):
        return "FAIL"
    if not evidences:
        return "FAIL"

    # NEEDS_REVIEW 조건
    # 1. 직접 탐지된 concept 중 근거 없는 항목 존재
    if missing_concepts:
        direct = list(decision.direct_concepts or []) if decision else []
        if any(c in direct for c in missing_concepts):
            return "NEEDS_REVIEW"
    # 2. 평균 evidence 신뢰도 낮음
    if avg_evidence_confidence is not None and avg_evidence_confidence < 0.75:
        return "NEEDS_REVIEW"

    return "PASS"


def _build_evidence_summary(
    evidences: list[EvidenceReference],
    all_concepts: list[str],
    answer_length: int,
) -> EvidenceSummaryResponse:
    evidence_concepts = {ev.concept_id for ev in evidences if ev.concept_id}
    missing = [c for c in all_concepts if c not in evidence_concepts]

    avg_conf = _avg([ev.confidence_score for ev in evidences])
    grounding = _compute_grounding_score(
        evidence_count=len(evidences),
        avg_evidence_confidence=avg_conf,
        answer_length=answer_length,
        missing_concepts_count=len(missing),
    )

    flags: list[str] = []
    if not evidences:
        flags.append("EVIDENCE_MISSING")
    elif avg_conf is not None and avg_conf < 0.60:
        flags.append("EVIDENCE_LOW_QUALITY")
    if missing:
        flags.append(f"MISSING_CONCEPTS: {', '.join(missing[:3])}")
    if grounding is not None and grounding < 0.60:
        flags.append("GROUNDING_WEAK")

    return EvidenceSummaryResponse(
        evidence_count=len(evidences),
        avg_evidence_confidence=avg_conf,
        avg_data_quality_score=_avg([ev.data_quality_score for ev in evidences]),
        avg_intent_relevance_score=_avg([ev.intent_relevance_score for ev in evidences]),
        missing_concepts=missing,
        grounding_score=grounding,
        review_flags=flags,
    )


def _compute_grounding_score(
    evidence_count: int,
    avg_evidence_confidence: float | None,
    answer_length: int,
    missing_concepts_count: int,
) -> float | None:
    # 추정값: evidence 품질 × answer 존재 여부 × concept 커버리지
    if avg_evidence_confidence is None:
        return None
    coverage = 1.0 if evidence_count > 0 else 0.0
    concept_penalty = max(0.0, 1.0 - missing_concepts_count * 0.15)
    answer_bonus = 1.0 if answer_length > 50 else 0.5
    return round(avg_evidence_confidence * coverage * concept_penalty * answer_bonus, 4)


def _build_leader_decision(
    decision: LeaderDecision | None,
    success_count: int,
    failed_count: int,
    unrouted_concepts: list[str],
    events: list[TraceEvent],
    score_breakdown: ScoreBreakdown | None,
) -> LeaderDecisionResponse:
    detected_concepts = list(decision.detected_concepts or []) if decision else []
    direct_concepts = list(decision.direct_concepts or []) if decision else []
    expanded_concepts = list(decision.expanded_concepts or []) if decision else []
    selected_agents = list(decision.selected_agents or []) if decision else []
    reasoning = decision.reasoning or {} if decision else {}
    intent_keywords = reasoning.get("keywords", []) if isinstance(reasoning, dict) else []
    intent_urgency = reasoning.get("urgency") if isinstance(reasoning, dict) else None

    return LeaderDecisionResponse(
        detected_intent=decision.detected_intent if decision else None,
        expected_intent=None,
        intent_match_yn=None,
        detected_concepts=detected_concepts,
        direct_concepts=direct_concepts,
        expanded_concepts=expanded_concepts,
        unrouted_concepts=unrouted_concepts,
        expected_concepts=[],
        missing_concepts=[],
        extra_concepts=[],
        selected_agents=selected_agents,
        expected_agents=[],
        missing_agents=[],
        extra_agents=[],
        step_count=decision.total_steps if decision and decision.total_steps is not None else success_count + failed_count,
        successful_step_count=success_count,
        failed_step_count=failed_count,
        leader_confidence_score=decision.confidence_score if decision else None,
        intent_keywords=intent_keywords,
        intent_urgency=intent_urgency,
        memory_turns=decision.memory_turns or 0 if decision else 0,
        ltm_turns=decision.ltm_turns or 0 if decision else 0,
        review_reason=decision.review_reason if decision else None,
        score_breakdown=score_breakdown,
    )


def _build_review(
    decision: LeaderDecision | None,
    evidences: list[EvidenceReference],
    avg_evidence_confidence: float | None,
    failed_step_count: int,
    events: list[TraceEvent],
    missing_concepts: list[str] | None = None,
) -> LeaderEvaluationReviewResponse:
    overall = _infer_overall_result(
        decision, evidences, avg_evidence_confidence, failed_step_count, events,
        missing_concepts=missing_concepts,
    )
    return LeaderEvaluationReviewResponse(
        final_answer_review=None,
        hallucination_yn=None,
        overall_result=overall,
        review_comment=None,
        reviewer=None,
        reviewed_at=None,
    )


def _serialize_trace_event(event: TraceEvent) -> LeaderEvaluationTraceEventResponse:
    return LeaderEvaluationTraceEventResponse(
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


def _build_content_preview(content: dict | None) -> dict | None:
    if not content or not isinstance(content, dict):
        return None
    for list_key in ["products", "rates", "policies", "documents", "branches", "histories"]:
        if list_key in content:
            items = content[list_key]
            return {list_key: items[:1] if items else []}
    return {k: v for k, v in list(content.items())[:3]}


def _serialize_evidence(ev: EvidenceReference) -> LeaderEvaluationEvidenceResponse:
    return LeaderEvaluationEvidenceResponse(
        id=ev.id,
        concept_id=ev.concept_id,
        source_id=ev.source_id,
        agent_id=ev.agent_id,
        confidence_score=ev.confidence_score,
        data_quality_score=ev.data_quality_score,
        intent_relevance_score=ev.intent_relevance_score,
        response_latency_ms=ev.response_latency_ms,
        item_count=ev.item_count,
        quality_flags=ev.quality_flags,
        related_evidence_ids=ev.related_evidence_ids,
        content_preview=_build_content_preview(ev.content),
        created_at=str(ev.created_at),
    )


@router.get("/leader-evaluations", response_model=LeaderEvaluationListResponse)
def list_leader_evaluations(
    limit: int = Query(20, ge=1, le=100),
    request_id: str | None = Query(default=None),
    overall_result: str | None = Query(default=None),
    detected_intent: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    query = db.query(TraceEvent)
    if request_id:
        query = query.filter(TraceEvent.request_id.contains(request_id))

    events = query.order_by(TraceEvent.created_at.desc(), TraceEvent.id.desc()).all()
    grouped: dict[str, list[TraceEvent]] = {}
    for event in events:
        grouped.setdefault(event.request_id, []).append(event)

    items: list[LeaderEvaluationListItemResponse] = []
    for current_request_id, request_events in grouped.items():
        ordered_events = sorted(request_events, key=lambda item: (item.created_at, item.id))
        decision = (
            db.query(LeaderDecision)
            .filter(LeaderDecision.request_id == current_request_id)
            .order_by(LeaderDecision.created_at.desc(), LeaderDecision.id.desc())
            .first()
        )
        if detected_intent and (decision is None or decision.detected_intent != detected_intent):
            continue

        evidences = (
            db.query(EvidenceReference)
            .filter(EvidenceReference.request_id == current_request_id)
            .all()
        )
        unrouted = _extract_unrouted_concepts(ordered_events)
        all_concepts = list(decision.detected_concepts or []) if decision else []
        evidence_summary = _build_evidence_summary(evidences, all_concepts, len(decision.answer or "") if decision else 0)

        success_count = sum(
            1 for e in ordered_events if e.event_type == "TOOL_INVOKED" and e.status == "success"
        )
        failed_count = sum(
            1 for e in ordered_events if e.event_type == "TOOL_INVOKED" and e.status != "success"
        )

        computed_result = _infer_overall_result(
            decision, evidences, evidence_summary.avg_evidence_confidence, failed_count, ordered_events,
            missing_concepts=evidence_summary.missing_concepts,
        )
        if overall_result and computed_result != overall_result:
            continue

        score_bd = _compute_score_breakdown(decision, evidences, unrouted, all_concepts)
        review_reason = _infer_review_reason(
            decision, evidences, failed_count, unrouted, ordered_events,
            missing_concepts=evidence_summary.missing_concepts,
        )

        request_event = _find_first_event(ordered_events, "REQUEST_RECEIVED")
        direct_concepts = list(decision.direct_concepts or []) if decision else []
        expanded_concepts = list(decision.expanded_concepts or []) if decision else []
        event_created_at = (
            str(request_event.created_at)
            if request_event
            else (str(ordered_events[0].created_at) if ordered_events else None)
        )

        items.append(
            LeaderEvaluationListItemResponse(
                request_id=current_request_id,
                user_question=(request_event.input_data or {}).get("message") if request_event else None,
                detected_intent=decision.detected_intent if decision else None,
                intent_match_yn=None,
                detected_concepts=all_concepts,
                direct_concepts=direct_concepts,
                expanded_concepts=expanded_concepts,
                unrouted_concepts=unrouted,
                selected_agents=list(decision.selected_agents or []) if decision else [],
                leader_confidence_score=decision.confidence_score if decision else None,
                avg_evidence_confidence=evidence_summary.avg_evidence_confidence,
                avg_data_quality_score=evidence_summary.avg_data_quality_score,
                avg_intent_relevance_score=evidence_summary.avg_intent_relevance_score,
                hallucination_yn=None,
                overall_result=computed_result,
                review_reason=review_reason,
                score_breakdown=score_bd,
                reviewer=None,
                reviewed_at=None,
                tool_success_count=success_count,
                tool_failed_count=failed_count,
                created_at=event_created_at,
            )
        )

    items.sort(key=lambda item: item.created_at or "", reverse=True)
    return LeaderEvaluationListResponse(items=items[:limit], total=len(items))


@router.get("/leader-evaluations/{request_id}", response_model=LeaderEvaluationDetailResponse)
def get_leader_evaluation_detail(
    request_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.request_id == request_id)
        .order_by(TraceEvent.id.asc())
        .all()
    )
    evidences = (
        db.query(EvidenceReference)
        .filter(EvidenceReference.request_id == request_id)
        .order_by(EvidenceReference.confidence_score.desc().nullslast())
        .all()
    )
    decision = (
        db.query(LeaderDecision)
        .filter(LeaderDecision.request_id == request_id)
        .order_by(LeaderDecision.created_at.desc(), LeaderDecision.id.desc())
        .first()
    )

    if not events and not evidences and decision is None:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' not found")

    request_event = _find_first_event(events, "REQUEST_RECEIVED")
    success_count = sum(
        1 for e in events if e.event_type == "TOOL_INVOKED" and e.status == "success"
    )
    failed_count = sum(
        1 for e in events if e.event_type == "TOOL_INVOKED" and e.status != "success"
    )
    unrouted = _extract_unrouted_concepts(events)
    all_concepts = list(decision.detected_concepts or []) if decision else []
    answer_text = decision.answer if decision else None
    evidence_summary = _build_evidence_summary(evidences, all_concepts, len(answer_text or ""))
    score_bd = _compute_score_breakdown(decision, evidences, unrouted, all_concepts)
    review_reason = _infer_review_reason(
        decision, evidences, failed_count, unrouted, events,
        missing_concepts=evidence_summary.missing_concepts,
    )

    # review_reason을 LeaderDecision에 업데이트 (DB에 캐시)
    if decision and decision.review_reason != review_reason:
        try:
            decision.review_reason = review_reason
            db.commit()
        except Exception:
            db.rollback()

    review = _build_review(
        decision, evidences, evidence_summary.avg_evidence_confidence, failed_count, events,
        missing_concepts=evidence_summary.missing_concepts,
    )

    return LeaderEvaluationDetailResponse(
        request_id=request_id,
        user_question=(request_event.input_data or {}).get("message") if request_event else None,
        answer=answer_text,
        leader_decision=_build_leader_decision(decision, success_count, failed_count, unrouted, events, score_bd),
        evidence_summary=evidence_summary,
        review=review,
        trace_events=[_serialize_trace_event(e) for e in events],
        evidences=[_serialize_evidence(ev) for ev in evidences],
    )


@router.delete("/leader-evaluations/{request_id}")
def delete_leader_evaluation(
    request_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    trace_count = db.query(TraceEvent).filter(TraceEvent.request_id == request_id).delete()
    evidence_count = db.query(EvidenceReference).filter(EvidenceReference.request_id == request_id).delete()
    decision_count = db.query(LeaderDecision).filter(LeaderDecision.request_id == request_id).delete()
    db.commit()

    if trace_count == 0 and evidence_count == 0 and decision_count == 0:
        raise HTTPException(status_code=404, detail=f"request_id '{request_id}' not found")

    return {"deleted": True, "request_id": request_id}
