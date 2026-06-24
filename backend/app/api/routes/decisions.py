"""
decisions.py — Decision Graph 조회 API

GET /api/v1/ai/decisions               : 목록 (페이지네이션)
GET /api/v1/ai/decisions/{id}          : 단건 요약
GET /api/v1/ai/decisions/{id}/graph    : React Flow용 nodes/edges JSON
POST /api/v1/ai/decisions/{id}/review  : 리뷰 저장 (ADMIN 전용)
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import AuthContext, Role, require_admin, require_readonly_context
from app.models.trace_model import (
    DecisionTrace,
    LeaderDecision,
    LeaderDecisionEdge,
    LeaderDecisionNode,
    LeaderDecisionReview,
    TraceEvent,
)
from app.schemas.decision_trace import DecisionTraceDetailResponse
from app.services.decision_trace_service import get_decision_trace_detail

router = APIRouter(prefix="/api/v1/ai", tags=["decisions"])


# ─────────────────────────────────────────────────────────────
# Response 스키마
# ─────────────────────────────────────────────────────────────

class DecisionListItem(BaseModel):
    request_id: str
    query_preview: str | None
    intent: str | None
    selected_agents: list[str]
    node_count: int
    edge_count: int
    tool_count: int
    review_status: str
    created_at: str


class DecisionListResponse(BaseModel):
    items: list[DecisionListItem]
    total: int
    page: int
    size: int


class GraphNodeResponse(BaseModel):
    id: str
    node_type: str
    label: str
    status: str
    position: dict[str, float]
    data: dict[str, Any]
    duration_ms: int | None


class GraphEdgeResponse(BaseModel):
    id: str
    edge_type: str
    source: str
    target: str
    label: str | None
    data: dict[str, Any]
    weight: float


class GraphSummary(BaseModel):
    intent: str | None
    selected_agents: list[str]
    node_count: int
    edge_count: int
    tool_count: int
    concept_count: int


class ReviewInfo(BaseModel):
    status: str
    reviewer_id: str | None
    overall_result: str | None
    intent_correct: bool | None
    concept_complete: bool | None
    agent_correct: bool | None
    evidence_sufficient: bool | None
    answer_appropriate: bool | None
    missing_concepts: list[str]
    wrong_agents: list[str]
    comment: str | None
    review_score: float | None
    reviewed_at: str | None


class DecisionGraphResponse(BaseModel):
    request_id: str
    created_at: str | None
    summary: GraphSummary
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    review: ReviewInfo


class ReviewRequest(BaseModel):
    overall_result: str                  # CORRECT / INCORRECT / PARTIAL
    intent_correct: bool | None = None
    concept_complete: bool | None = None
    agent_correct: bool | None = None
    evidence_sufficient: bool | None = None
    answer_appropriate: bool | None = None
    missing_concepts: list[str] = []
    wrong_agents: list[str] = []
    comment: str | None = None
    review_score: float | None = None


# ─────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────

def _fmt_dt(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _get_query_preview(db: Session, request_id: str) -> str | None:
    node = (
        db.query(LeaderDecisionNode)
        .filter_by(request_id=request_id, node_type="USER_QUERY")
        .first()
    )
    if node and node.data:
        msg = node.data.get("message", "")
        return msg[:40] if msg else None
    return None


def _get_review(db: Session, request_id: str) -> LeaderDecisionReview | None:
    return db.query(LeaderDecisionReview).filter_by(request_id=request_id).first()


def _apply_decision_scope(query, auth: AuthContext):
    if auth.role == Role.ADMIN:
        return query

    owned_request_ids = select(DecisionTrace.request_id).where(
        DecisionTrace.owner_name == auth.name
    )
    return query.filter(LeaderDecisionNode.request_id.in_(owned_request_ids))


def _ensure_decision_access(db: Session, auth: AuthContext, request_id: str) -> None:
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
        raise HTTPException(status_code=404, detail="Decision graph not found")


def _build_memory_write_nodes(
    db: Session,
    request_id: str,
    final_node_id: str | None,
) -> tuple[list[GraphNodeResponse], list[GraphEdgeResponse]]:
    if not final_node_id:
        return [], []

    events = (
        db.query(TraceEvent)
        .filter(
            TraceEvent.request_id == request_id,
            TraceEvent.event_type.in_(["MEMORY_SAVED", "LTM_SAVED"]),
        )
        .order_by(TraceEvent.created_at.asc())
        .all()
    )
    if not events:
        return [], []

    synthetic_nodes: list[GraphNodeResponse] = []
    synthetic_edges: list[GraphEdgeResponse] = []
    base_x = 280.0
    step_x = 260.0
    y = 1220.0

    for index, event in enumerate(events):
        node_id = f"node_memory_write_{request_id.replace('-', '')[:8]}_{index + 1:03d}"
        output_data = event.output_data or {}
        memory_type = "SHORT" if event.event_type == "MEMORY_SAVED" else "LTM"
        label = "Short Memory Save" if memory_type == "SHORT" else "Long-term Memory Save"
        synthetic_nodes.append(
            GraphNodeResponse(
                id=node_id,
                node_type="MEMORY_WRITE",
                label=label,
                status="SUCCESS" if output_data.get("saved") else "FAILED",
                position={"x": base_x + index * step_x, "y": y},
                data={
                    "memory_type": memory_type,
                    "saved": output_data.get("saved", False),
                    "stored_turns": output_data.get("stored_turns"),
                    "turn_index": output_data.get("turn_index"),
                    "question_summary": output_data.get("question_summary"),
                    "answer_summary": output_data.get("answer_summary"),
                    "preview": output_data.get("preview", []),
                    "reason": output_data.get("reason"),
                },
                duration_ms=event.duration_ms,
            )
        )
        synthetic_edges.append(
            GraphEdgeResponse(
                id=f"edge_memory_write_{request_id.replace('-', '')[:8]}_{index + 1:03d}",
                edge_type="SAVES_MEMORY",
                source=final_node_id,
                target=node_id,
                label="save",
                data={"memory_type": memory_type},
                weight=1.0,
            )
        )

    return synthetic_nodes, synthetic_edges


# ─────────────────────────────────────────────────────────────
# 목록 API
# ─────────────────────────────────────────────────────────────

@router.get("/decisions", response_model=DecisionListResponse)
def list_decisions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    intent: str | None = Query(None),
    review_status: str | None = Query(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    """Decision Graph 목록을 최신순으로 반환한다."""
    # USER_QUERY 노드 기준으로 페이지네이션 (요청당 1개 존재)
    q = db.query(LeaderDecisionNode).filter(
        LeaderDecisionNode.node_type == "USER_QUERY"
    )
    q = _apply_decision_scope(q, auth)

    # leader_decision에서 intent 필터
    if intent:
        matched_ids = [
            r.request_id
            for r in db.query(LeaderDecision.request_id)
            .filter(LeaderDecision.detected_intent == intent)
            .all()
        ]
        q = q.filter(LeaderDecisionNode.request_id.in_(matched_ids))

    total = q.count()
    user_query_nodes = (
        q.order_by(LeaderDecisionNode.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    request_ids = [n.request_id for n in user_query_nodes]

    # 배치 조회 — request_id IN (...)
    decisions_map: dict[str, LeaderDecision] = {
        d.request_id: d
        for d in db.query(LeaderDecision)
        .filter(LeaderDecision.request_id.in_(request_ids))
        .all()
    }

    node_counts: dict[str, int] = {
        row[0]: row[1]
        for row in db.query(
            LeaderDecisionNode.request_id,
            func.count(LeaderDecisionNode.id),
        )
        .filter(LeaderDecisionNode.request_id.in_(request_ids))
        .group_by(LeaderDecisionNode.request_id)
        .all()
    }

    edge_counts: dict[str, int] = {
        row[0]: row[1]
        for row in db.query(
            LeaderDecisionEdge.request_id,
            func.count(LeaderDecisionEdge.id),
        )
        .filter(LeaderDecisionEdge.request_id.in_(request_ids))
        .group_by(LeaderDecisionEdge.request_id)
        .all()
    }

    tool_counts: dict[str, int] = {
        row[0]: row[1]
        for row in db.query(
            LeaderDecisionNode.request_id,
            func.count(LeaderDecisionNode.id),
        )
        .filter(
            LeaderDecisionNode.request_id.in_(request_ids),
            LeaderDecisionNode.node_type == "TOOL_CALL",
        )
        .group_by(LeaderDecisionNode.request_id)
        .all()
    }

    reviews_map: dict[str, LeaderDecisionReview] = {
        r.request_id: r
        for r in db.query(LeaderDecisionReview)
        .filter(LeaderDecisionReview.request_id.in_(request_ids))
        .all()
    }

    items: list[DecisionListItem] = []
    for node in user_query_nodes:
        rid = node.request_id
        decision = decisions_map.get(rid)
        review = reviews_map.get(rid)

        # review_status 필터 적용
        r_status = review.status if review else "PENDING"
        if review_status and r_status != review_status:
            continue

        items.append(DecisionListItem(
            request_id=rid,
            query_preview=node.data.get("message", "")[:40] if node.data else None,
            intent=decision.detected_intent if decision else None,
            selected_agents=decision.selected_agents or [] if decision else [],
            node_count=node_counts.get(rid, 0),
            edge_count=edge_counts.get(rid, 0),
            tool_count=tool_counts.get(rid, 0),
            review_status=r_status,
            created_at=_fmt_dt(node.created_at) or "",
        ))

    return DecisionListResponse(items=items, total=total, page=page, size=size)


# ─────────────────────────────────────────────────────────────
# 그래프 API
# ─────────────────────────────────────────────────────────────

@router.get("/decisions/{request_id}/graph", response_model=DecisionGraphResponse)
def get_decision_graph(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    """React Flow에서 바로 렌더링 가능한 nodes/edges JSON을 반환한다."""
    _ensure_decision_access(db, auth, request_id)
    nodes = (
        db.query(LeaderDecisionNode)
        .filter_by(request_id=request_id)
        .order_by(LeaderDecisionNode.sequence_order)
        .all()
    )
    if not nodes:
        raise HTTPException(status_code=404, detail="Decision graph not found")

    edges = (
        db.query(LeaderDecisionEdge)
        .filter_by(request_id=request_id)
        .all()
    )

    review = _get_review(db, request_id)
    decision = db.query(LeaderDecision).filter_by(request_id=request_id).first()

    # 요약 계산
    selected_agents = decision.selected_agents or [] if decision else []
    tool_nodes = [n for n in nodes if n.node_type == "TOOL_CALL"]
    concept_nodes = [n for n in nodes if n.node_type == "CONCEPT"]
    first_node = nodes[0] if nodes else None

    summary = GraphSummary(
        intent=decision.detected_intent if decision else None,
        selected_agents=selected_agents,
        node_count=len(nodes),
        edge_count=len(edges),
        tool_count=len(tool_nodes),
        concept_count=len(concept_nodes),
    )

    graph_nodes = [
        GraphNodeResponse(
            id=n.node_id,
            node_type=n.node_type,
            label=n.node_label or "",
            status=n.status,
            position={"x": n.position_x or 0.0, "y": n.position_y or 0.0},
            data=n.data or {},
            duration_ms=n.duration_ms,
        )
        for n in nodes
    ]

    graph_edges = [
        GraphEdgeResponse(
            id=e.edge_id,
            edge_type=e.edge_type,
            source=e.source_node_id,
            target=e.target_node_id,
            label=e.edge_label,
            data=e.data or {},
            weight=e.weight or 1.0,
        )
        for e in edges
    ]

    if not any(node.node_type == "MEMORY_WRITE" for node in graph_nodes):
        final_node = next((node for node in graph_nodes if node.node_type == "FINAL_RESPONSE"), None)
        memory_nodes, memory_edges = _build_memory_write_nodes(
            db,
            request_id,
            final_node.id if final_node else None,
        )
        graph_nodes.extend(memory_nodes)
        graph_edges.extend(memory_edges)

    return DecisionGraphResponse(
        request_id=request_id,
        created_at=_fmt_dt(first_node.created_at) if first_node else None,
        summary=summary,
        nodes=graph_nodes,
        edges=graph_edges,
        review=ReviewInfo(
            status=review.status if review else "PENDING",
            reviewer_id=review.reviewer_id if review else None,
            overall_result=review.overall_result if review else None,
            intent_correct=review.intent_correct if review else None,
            concept_complete=review.concept_complete if review else None,
            agent_correct=review.agent_correct if review else None,
            evidence_sufficient=review.evidence_sufficient if review else None,
            answer_appropriate=review.answer_appropriate if review else None,
            missing_concepts=review.missing_concepts or [] if review else [],
            wrong_agents=review.wrong_agents or [] if review else [],
            comment=review.comment if review else None,
            review_score=review.review_score if review else None,
            reviewed_at=_fmt_dt(review.reviewed_at) if review else None,
        ),
    )


# ─────────────────────────────────────────────────────────────
# 리뷰 저장 API
# ─────────────────────────────────────────────────────────────

@router.get("/decisions/{request_id}/trace", response_model=DecisionTraceDetailResponse)
def get_decision_trace(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    _ensure_decision_access(db, auth, request_id)
    trace = get_decision_trace_detail(db, request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Decision trace not found")
    return trace


@router.post("/decisions/{request_id}/review")
def save_review(
    request_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    role: Role = Depends(require_admin),
):
    """Reviewer가 Decision Graph 평가 결과를 저장한다 (ADMIN 전용)."""
    existing = db.query(LeaderDecisionReview).filter_by(request_id=request_id).first()

    if existing:
        existing.overall_result      = body.overall_result
        existing.intent_correct      = body.intent_correct
        existing.concept_complete    = body.concept_complete
        existing.agent_correct       = body.agent_correct
        existing.evidence_sufficient = body.evidence_sufficient
        existing.answer_appropriate  = body.answer_appropriate
        existing.missing_concepts    = body.missing_concepts
        existing.wrong_agents        = body.wrong_agents
        existing.comment             = body.comment
        existing.review_score        = body.review_score
        existing.status              = "APPROVED" if body.overall_result == "CORRECT" else "REJECTED"
        existing.reviewed_at         = datetime.utcnow()
    else:
        db.add(LeaderDecisionReview(
            request_id=request_id,
            overall_result=body.overall_result,
            intent_correct=body.intent_correct,
            concept_complete=body.concept_complete,
            agent_correct=body.agent_correct,
            evidence_sufficient=body.evidence_sufficient,
            answer_appropriate=body.answer_appropriate,
            missing_concepts=body.missing_concepts,
            wrong_agents=body.wrong_agents,
            comment=body.comment,
            review_score=body.review_score,
            status="APPROVED" if body.overall_result == "CORRECT" else "REJECTED",
            reviewed_at=datetime.utcnow(),
        ))

    db.commit()
    return {"saved": True, "status": "APPROVED" if body.overall_result == "CORRECT" else "REJECTED"}
