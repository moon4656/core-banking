"""leader_monitor.py — Leader Agent mon_* 테이블 조회 API

[엔드포인트]
  GET /api/v1/leader-agent/traces
      — 트레이스 목록 (페이지네이션, status 필터)

  GET /api/v1/leader-agent/traces/{request_id}
      — 특정 request_id의 전체 상세 (7개 mon_* 테이블 조합)

  GET /api/v1/leader-agent/traces/{request_id}/gates
      — Gate 1·2·3 체크 결과만 반환
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import AuthContext, Role, require_readonly_context
from app.models.monitor_model import (
    MonAgentTrace,
    MonAnswerSentence,
    MonConceptDetection,
    MonGateCheck,
    MonIntentAnalysis,
    MonRoutingDecision,
    MonToolExecution,
)
from app.schemas.monitor_schema import (
    MonConceptDetail,
    MonGateDetail,
    MonGatesResponse,
    MonIntentDetail,
    MonRoutingDetail,
    MonSentenceDetail,
    MonToolDetail,
    MonTraceDetailResponse,
    MonTraceListItem,
    MonTraceListResponse,
)

router = APIRouter(prefix="/api/v1/leader-agent", tags=["leader-agent-monitor"])


def _apply_monitor_scope(query, auth: AuthContext):
    if auth.role == Role.ADMIN:
        return query
    return query.filter(MonAgentTrace.user_id == auth.name)


def _ensure_monitor_access(db: Session, auth: AuthContext, request_id: str) -> MonAgentTrace:
    query = db.query(MonAgentTrace).filter(MonAgentTrace.request_id == request_id)
    query = _apply_monitor_scope(query, auth)
    trace = query.first()
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace '{request_id}' not found")
    return trace


# ── 목록 조회 ──────────────────────────────────────────────────────────────

@router.get("/traces", response_model=MonTraceListResponse, summary="트레이스 목록 조회")
def list_traces(
    page: int = Query(default=1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    status: str | None = Query(default=None, description="상태 필터 (processing|completed|warning|blocked|failed)"),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    """
    Leader Agent 파이프라인 요청 이력 목록을 반환한다.

    - **page**: 1부터 시작하는 페이지 번호
    - **size**: 한 페이지에 반환할 최대 건수 (최대 100)
    - **status**: 필터링할 상태값. 미입력 시 전체 반환.
    """
    query = db.query(MonAgentTrace)
    query = _apply_monitor_scope(query, auth)
    if status:
        query = query.filter(MonAgentTrace.status == status)

    total = query.count()
    rows = (
        query
        .order_by(MonAgentTrace.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return MonTraceListResponse(
        total=total,
        page=page,
        size=size,
        items=[MonTraceListItem.model_validate(r) for r in rows],
    )


# ── 상세 조회 ──────────────────────────────────────────────────────────────

@router.get(
    "/traces/{request_id}",
    response_model=MonTraceDetailResponse,
    summary="트레이스 전체 상세 조회",
)
def get_trace_detail(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    """
    특정 request_id의 모니터링 데이터를 7개 섹션으로 반환한다.

    - **trace**: 요청 헤더 (상태, 레이턴시, 쿼리)
    - **intent**: 의도 분석 결과
    - **concepts**: Concept 탐지 목록 (confidence 포함)
    - **routing**: Agent 라우팅 결정 (선택/제외 사유)
    - **tools**: Tool 실행 이력 (입력·출력·레이턴시)
    - **sentences**: 답변 문장별 근거 추적 (grounded 여부)
    - **gates**: Gate 1·2·3 체크 결과
    """
    trace = _ensure_monitor_access(db, auth, request_id)

    intent_row = (
        db.query(MonIntentAnalysis)
        .filter(MonIntentAnalysis.request_id == request_id)
        .first()
    )

    concept_rows = (
        db.query(MonConceptDetection)
        .filter(MonConceptDetection.request_id == request_id)
        .order_by(MonConceptDetection.id)
        .all()
    )

    routing_rows = (
        db.query(MonRoutingDecision)
        .filter(MonRoutingDecision.request_id == request_id)
        .order_by(MonRoutingDecision.execution_order.nullslast(), MonRoutingDecision.id)
        .all()
    )

    tool_rows = (
        db.query(MonToolExecution)
        .filter(MonToolExecution.request_id == request_id)
        .order_by(MonToolExecution.id)
        .all()
    )

    sentence_rows = (
        db.query(MonAnswerSentence)
        .filter(MonAnswerSentence.request_id == request_id)
        .order_by(MonAnswerSentence.id)
        .all()
    )

    gate_rows = (
        db.query(MonGateCheck)
        .filter(MonGateCheck.request_id == request_id)
        .order_by(MonGateCheck.id)
        .all()
    )

    return MonTraceDetailResponse(
        trace=MonTraceListItem.model_validate(trace),
        intent=MonIntentDetail.model_validate(intent_row) if intent_row else None,
        concepts=[MonConceptDetail.model_validate(r) for r in concept_rows],
        routing=[MonRoutingDetail.model_validate(r) for r in routing_rows],
        tools=[MonToolDetail.model_validate(r) for r in tool_rows],
        sentences=[MonSentenceDetail.model_validate(r) for r in sentence_rows],
        gates=[MonGateDetail.model_validate(r) for r in gate_rows],
    )


# ── Gate 전용 조회 ─────────────────────────────────────────────────────────

@router.get(
    "/traces/{request_id}/gates",
    response_model=MonGatesResponse,
    summary="Gate 체크 결과 조회",
)
def get_trace_gates(
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_readonly_context),
):
    """
    특정 request_id의 Gate 1·2·3 체크 결과만 반환한다.

    - **overall_status**: 해당 요청의 최종 상태 (completed|warning|blocked|…)
    - **gates**: Gate별 결과 (PASS|WARNING|BLOCKED) 및 메시지
    """
    trace = _ensure_monitor_access(db, auth, request_id)

    gate_rows = (
        db.query(MonGateCheck)
        .filter(MonGateCheck.request_id == request_id)
        .order_by(MonGateCheck.id)
        .all()
    )

    return MonGatesResponse(
        request_id=request_id,
        overall_status=trace.status or "unknown",
        gates=[MonGateDetail.model_validate(r) for r in gate_rows],
    )
