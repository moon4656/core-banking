from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.trace_model import (
    AgentSelectionTrace,
    ConceptDetectionTrace,
    DecisionTrace,
    FinalAnswerTrace,
    LeaderDecision,
    RerankingTrace,
    ToolExecutionTrace,
)
from app.schemas.decision_trace import (
    AgentSelectionItemResponse,
    ConceptTraceResponse,
    DecisionTraceDetailResponse,
    IntentAnalysisResponse,
    LeaderDecisionResponse,
    MemoryBucket,
    MemoryItem,
    ToolExecutionResponse,
)


def save_decision_trace_core(
    db: Session,
    *,
    request_id: str,
    session_id: str | None,
    owner_name: str | None,
    owner_role: str | None,
    user_query: str,
    normalized_query: str,
    request_meta: dict[str, Any],
    memory_summary: dict[str, Any],
    intent_analysis: dict[str, Any],
    latency: dict[str, Any],
    status: str = "completed",
) -> None:
    db.add(
        DecisionTrace(
            request_id=request_id,
            session_id=session_id,
            owner_name=owner_name,
            owner_role=owner_role,
            user_query=user_query,
            normalized_query=normalized_query,
            request_meta=request_meta,
            memory_summary=memory_summary,
            intent_analysis=intent_analysis,
            latency=latency,
            status=status,
        )
    )


def save_concept_detections(db: Session, request_id: str, concepts: list[dict[str, Any]]) -> None:
    for concept in concepts:
        db.add(
            ConceptDetectionTrace(
                request_id=request_id,
                concept_id=concept["concept_id"],
                detection_stage=concept["detection_stage"],
                confidence=concept.get("confidence"),
                source_type=concept.get("source_type"),
                source_terms=concept.get("source_terms", []),
                relation_path=concept.get("relation_path", []),
                reason=concept.get("reason"),
            )
        )


def save_agent_selection_rows(db: Session, request_id: str, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        db.add(
            AgentSelectionTrace(
                request_id=request_id,
                agent_id=row["agent_id"],
                selected=row["selected"],
                score=row.get("score"),
                matched_concepts=row.get("matched_concepts", []),
                reason=row["reason"],
                rejection_reason=row.get("rejection_reason"),
                role=row.get("role"),
                execution_mode=row.get("execution_mode"),
                tools_assigned=row.get("tools_assigned", []),
                decision_rule_ids=row.get("decision_rule_ids", []),
            )
        )


def save_tool_execution_rows(db: Session, request_id: str, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        db.add(
            ToolExecutionTrace(
                request_id=request_id,
                agent_id=row["agent_id"],
                tool_code=row["tool_code"],
                concept_ids=row.get("concept_ids", []),
                input_summary=row.get("input_summary"),
                output_summary=row.get("output_summary"),
                status=row["status"],
                latency_ms=row.get("latency_ms"),
                error_summary=row.get("error_summary"),
                evidence_ids=row.get("evidence_ids", []),
            )
        )


def save_reranking_trace(
    db: Session,
    *,
    request_id: str,
    criteria_weights: dict[str, Any],
    candidates: list[dict[str, Any]],
    selected_evidence_ids: list[int],
    reason: str,
) -> None:
    db.add(
        RerankingTrace(
            request_id=request_id,
            criteria_weights=criteria_weights,
            candidates=candidates,
            selected_evidence_ids=selected_evidence_ids,
            reason=reason,
        )
    )


def save_final_answer_trace(
    db: Session,
    *,
    request_id: str,
    answer: str,
    answer_summary: str,
    used_evidence_ids: list[int],
    grounding_summary: str,
) -> None:
    db.add(
        FinalAnswerTrace(
            request_id=request_id,
            answer=answer,
            answer_summary=answer_summary,
            used_evidence_ids=used_evidence_ids,
            grounding_summary=grounding_summary,
        )
    )


def get_decision_trace_detail(db: Session, request_id: str) -> DecisionTraceDetailResponse | None:
    trace = db.query(DecisionTrace).filter(DecisionTrace.request_id == request_id).first()
    if trace is None:
        return None

    concept_rows = (
        db.query(ConceptDetectionTrace)
        .filter(ConceptDetectionTrace.request_id == request_id)
        .order_by(ConceptDetectionTrace.id.asc())
        .all()
    )
    agent_rows = (
        db.query(AgentSelectionTrace)
        .filter(AgentSelectionTrace.request_id == request_id)
        .order_by(AgentSelectionTrace.id.asc())
        .all()
    )
    tool_rows = (
        db.query(ToolExecutionTrace)
        .filter(ToolExecutionTrace.request_id == request_id)
        .order_by(ToolExecutionTrace.id.asc())
        .all()
    )
    rerank = db.query(RerankingTrace).filter(RerankingTrace.request_id == request_id).first()
    final = db.query(FinalAnswerTrace).filter(FinalAnswerTrace.request_id == request_id).first()
    leader = db.query(LeaderDecision).filter(LeaderDecision.request_id == request_id).first()

    memory_summary = trace.memory_summary or {}
    memory = {
        "short_memory": MemoryBucket(**(memory_summary.get("short_memory") or {"loaded": False})),
        "long_term_memory": MemoryBucket(**(memory_summary.get("long_term_memory") or {"loaded": False})),
    }
    intent_payload = trace.intent_analysis or {}

    selected_agents: list[AgentSelectionItemResponse] = []
    rejected_agents: list[AgentSelectionItemResponse] = []
    for row in agent_rows:
        if row.agent_id == "LEADER_AGENT":
            continue
        item = AgentSelectionItemResponse(
            agent_name=row.agent_id,
            selected=row.selected,
            score=row.score,
            matched_concepts=row.matched_concepts or [],
            reason=row.reason,
            rejection_reason=row.rejection_reason,
        )
        if row.selected:
            selected_agents.append(item)
        else:
            rejected_agents.append(item)

    leader_reasoning = leader.reasoning if leader and leader.reasoning else {}
    leader_decision = LeaderDecisionResponse(
        description=(
            "Detected concepts were mapped to sub-agents through concept-to-agent routing."
            if leader
            else None
        ),
        selected_agents=leader.selected_agents or [] if leader else [],
        rejected_agents=[item.agent_name for item in rejected_agents],
        direct_concepts=leader.direct_concepts or [] if leader else [],
        expanded_concepts=leader.expanded_concepts or [] if leader else [],
        unrouted_concepts=leader_reasoning.get("unrouted_concepts", []) if leader_reasoning else [],
        confidence=leader.confidence_score if leader else None,
        total_steps=leader.total_steps if leader else None,
        reason=leader_reasoning.get("leader_reason")
        if leader_reasoning
        else None,
    )

    return DecisionTraceDetailResponse(
        request_id=trace.request_id,
        user_query=trace.user_query,
        normalized_query=trace.normalized_query,
        memory=memory,
        intent_analysis=IntentAnalysisResponse(
            intent=intent_payload.get("intent"),
            confidence=intent_payload.get("confidence"),
            keywords=intent_payload.get("keywords", []),
            urgency=intent_payload.get("urgency"),
            reason=intent_payload.get("reason"),
        ),
        leader_decision=leader_decision,
        concepts=[
            ConceptTraceResponse(
                concept_id=row.concept_id,
                detection_stage=row.detection_stage,
                confidence=row.confidence,
                source_type=row.source_type,
                source_terms=row.source_terms or [],
                reason=row.reason,
            )
            for row in concept_rows
        ],
        agent_selection={
            "selected_agents": selected_agents,
            "rejected_agents": rejected_agents,
        },
        tool_executions=[
            ToolExecutionResponse(
                tool_name=row.tool_code,
                agent_name=row.agent_id,
                concept_ids=row.concept_ids or [],
                input_summary=row.input_summary,
                output_summary=row.output_summary,
                status=row.status,
                latency_ms=row.latency_ms,
                evidence_ids=row.evidence_ids or [],
            )
            for row in tool_rows
        ],
        reranking={
            "criteria_weights": rerank.criteria_weights if rerank else {},
            "candidates": rerank.candidates if rerank else [],
            "selected_evidence_ids": rerank.selected_evidence_ids if rerank else [],
            "reason": rerank.reason if rerank else None,
        },
        final_answer={
            "answer": final.answer if final else "",
            "answer_summary": final.answer_summary if final else None,
            "used_evidence_ids": final.used_evidence_ids if final else [],
            "grounding_summary": final.grounding_summary if final else None,
        },
        latency=trace.latency or {},
    )
