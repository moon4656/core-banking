"""
monitoring.py — 실시간 Agent 모니터링 API

[엔드포인트]
  GET /api/v1/monitoring/stream/{request_id}   SSE: 특정 요청의 파이프라인 이벤트 실시간 스트림
  GET /api/v1/monitoring/latest                최근 request_id 반환 (프론트 폴링용)
  GET /api/v1/monitoring/metrics               집계 통계 (24시간 기본)

[SSE 방식]
  DB 폴링(200ms 간격): trace_event 테이블에서 새 이벤트를 읽어 스트림으로 전달.
  별도 메시지 큐 없이 기존 DB 기록만 활용하므로 코드 변경 최소화.
  RESPONSE_COMPLETED 이벤트 수신 시 스트림 종료 (최대 90초 타임아웃).
"""

import asyncio
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.trace_model import EvidenceReference, LeaderDecision, TraceEvent

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# 파이프라인 단계 레이블 (프론트 표시용)
_EVENT_LABEL: dict[str, str] = {
    "REQUEST_RECEIVED":   "요청 수신",
    "MEMORY_LOADED":      "Short Memory 로드",
    "LTM_LOADED":         "Long-term Memory 로드",
    "INTENT_ANALYZED":    "의도 분석",
    "CONCEPT_DETECTED":   "Concept 탐지",
    "AGENT_SELECTED":     "Agent 라우팅",
    "PLAN_CREATED":       "실행 계획 생성",
    "TOOL_INVOKED":       "Tool 실행",
    "RESULTS_RERANKED":   "결과 재정렬",
    "MEMORY_SAVED":       "Memory 저장",
    "LTM_SAVED":          "Long-term Memory 저장",
    "RESPONSE_COMPLETED": "응답 완료",
}


# ──────────────────────────────────────────────
# SSE 스트림 엔드포인트
# ──────────────────────────────────────────────

@router.get("/stream/{request_id}", include_in_schema=False)
async def stream_pipeline(
    request_id: str,
    db: Session = Depends(get_db),
):
    """
    특정 request_id 의 파이프라인 이벤트를 SSE로 스트림한다.

    - DB trace_event 테이블을 200ms 간격으로 폴링
    - RESPONSE_COMPLETED 이벤트 도달 시 자동 종료
    - 최대 90초 유지 후 __TIMEOUT__ 이벤트 전송 후 종료
    """
    async def generate():
        last_id = 0
        deadline = asyncio.get_event_loop().time() + 90.0

        while asyncio.get_event_loop().time() < deadline:
            rows = (
                db.query(TraceEvent)
                .filter(
                    TraceEvent.request_id == request_id,
                    TraceEvent.id > last_id,
                )
                .order_by(TraceEvent.id)
                .all()
            )

            for row in rows:
                last_id = row.id
                payload = {
                    "id":         row.id,
                    "event_type": row.event_type,
                    "label":      _EVENT_LABEL.get(row.event_type, row.event_type),
                    "agent_id":   row.agent_id,
                    "tool_id":    row.tool_id,
                    "status":     row.status,
                    "duration_ms": row.duration_ms,
                    "output_data": row.output_data,
                    "ts":         row.created_at.isoformat() if row.created_at else None,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                if row.event_type == "RESPONSE_COMPLETED":
                    yield f"data: {json.dumps({'event_type': '__DONE__'})}\n\n"
                    return

            await asyncio.sleep(0.2)

        yield f"data: {json.dumps({'event_type': '__TIMEOUT__'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


# ──────────────────────────────────────────────
# 최근 request_id 조회
# ──────────────────────────────────────────────

@router.get("/latest")
def get_latest_request(db: Session = Depends(get_db)):
    """최근 처리된 request_id를 반환한다. 프론트에서 3초 폴링으로 SSE 재연결에 활용."""
    row = (
        db.query(TraceEvent.request_id, TraceEvent.created_at)
        .order_by(TraceEvent.id.desc())
        .first()
    )
    if not row:
        return {"request_id": None, "created_at": None}
    return {
        "request_id": row.request_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ──────────────────────────────────────────────
# 집계 메트릭 엔드포인트
# ──────────────────────────────────────────────

@router.get("/metrics")
def get_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="집계 기간 (시간)"),
    db: Session = Depends(get_db),
):
    """
    Agent/Tool 실행 통계를 반환한다.

    [반환 데이터]
    - summary: 총 요청 수, 성공률, 평균 지연, 오류 수
    - intent_distribution: 의도별 요청 분포
    - agent_stats: Agent별 호출 횟수, 성공률, 평균 지연
    - tool_stats:  Tool별 호출 횟수, 성공률, 평균 지연
    - recent_errors: 최근 오류 이벤트 5건
    - pipeline_latency: 파이프라인 단계별 평균 지연
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    # ── 전체 요청 수 / 오류 수 ────────────────────────────────
    total_requests = (
        db.query(func.count(func.distinct(TraceEvent.request_id)))
        .filter(TraceEvent.created_at >= since)
        .scalar()
        or 0
    )
    error_count = (
        db.query(func.count(TraceEvent.id))
        .filter(TraceEvent.created_at >= since, TraceEvent.status == "error")
        .scalar()
        or 0
    )

    # 완료된 요청 = RESPONSE_COMPLETED 이벤트가 있는 request_id
    completed_ids = (
        db.query(func.distinct(TraceEvent.request_id))
        .filter(
            TraceEvent.created_at >= since,
            TraceEvent.event_type == "RESPONSE_COMPLETED",
        )
        .all()
    )
    completed_count = len(completed_ids)
    success_rate = round(completed_count / total_requests, 4) if total_requests else 0.0

    # 평균 전체 지연 (RESPONSE_COMPLETED duration_ms)
    avg_latency_row = (
        db.query(func.avg(TraceEvent.duration_ms))
        .filter(
            TraceEvent.created_at >= since,
            TraceEvent.event_type == "RESPONSE_COMPLETED",
            TraceEvent.duration_ms.isnot(None),
        )
        .scalar()
    )
    avg_latency_ms = round(float(avg_latency_row), 1) if avg_latency_row else 0.0

    # ── 의도 분포 (leader_decision 테이블) ────────────────────
    intent_rows = (
        db.query(LeaderDecision.detected_intent, func.count(LeaderDecision.id))
        .filter(LeaderDecision.created_at >= since)
        .group_by(LeaderDecision.detected_intent)
        .all()
    )
    intent_distribution = {
        (row[0] or "UNKNOWN"): row[1] for row in intent_rows
    }

    # ── Agent 통계 (TOOL_INVOKED 이벤트의 agent_id) ───────────
    agent_rows = (
        db.query(
            TraceEvent.agent_id,
            func.count(TraceEvent.id).label("call_count"),
            func.sum(
                func.cast(TraceEvent.status == "success", Integer_)
            ).label("success_count"),
            func.avg(TraceEvent.duration_ms).label("avg_latency"),
        )
        .filter(
            TraceEvent.created_at >= since,
            TraceEvent.event_type == "TOOL_INVOKED",
            TraceEvent.agent_id.isnot(None),
        )
        .group_by(TraceEvent.agent_id)
        .all()
    )
    agent_stats = [
        {
            "agent_id":      row.agent_id,
            "call_count":    row.call_count,
            "success_rate":  round((row.success_count or 0) / row.call_count, 4) if row.call_count else 0.0,
            "avg_latency_ms": round(float(row.avg_latency), 1) if row.avg_latency else 0.0,
        }
        for row in agent_rows
    ]

    # ── Tool 통계 (TOOL_INVOKED 이벤트의 tool_id) ────────────
    tool_rows = (
        db.query(
            TraceEvent.tool_id,
            func.count(TraceEvent.id).label("call_count"),
            func.sum(
                func.cast(TraceEvent.status == "success", Integer_)
            ).label("success_count"),
            func.avg(TraceEvent.duration_ms).label("avg_latency"),
        )
        .filter(
            TraceEvent.created_at >= since,
            TraceEvent.event_type == "TOOL_INVOKED",
            TraceEvent.tool_id.isnot(None),
        )
        .group_by(TraceEvent.tool_id)
        .all()
    )
    tool_stats = [
        {
            "tool_id":       row.tool_id,
            "call_count":    row.call_count,
            "success_rate":  round((row.success_count or 0) / row.call_count, 4) if row.call_count else 0.0,
            "avg_latency_ms": round(float(row.avg_latency), 1) if row.avg_latency else 0.0,
        }
        for row in tool_rows
    ]

    # ── 파이프라인 단계별 평균 지연 ──────────────────────────
    pipeline_events = [
        "INTENT_ANALYZED", "CONCEPT_DETECTED", "AGENT_SELECTED",
        "PLAN_CREATED", "RESULTS_RERANKED", "RESPONSE_COMPLETED",
    ]
    pipeline_rows = (
        db.query(
            TraceEvent.event_type,
            func.avg(TraceEvent.duration_ms).label("avg_ms"),
            func.count(TraceEvent.id).label("cnt"),
        )
        .filter(
            TraceEvent.created_at >= since,
            TraceEvent.event_type.in_(pipeline_events),
            TraceEvent.duration_ms.isnot(None),
        )
        .group_by(TraceEvent.event_type)
        .all()
    )
    pipeline_latency = [
        {
            "event_type": row.event_type,
            "label":      _EVENT_LABEL.get(row.event_type, row.event_type),
            "avg_ms":     round(float(row.avg_ms), 1) if row.avg_ms else 0.0,
            "count":      row.cnt,
        }
        for row in sorted(pipeline_rows, key=lambda r: pipeline_events.index(r.event_type) if r.event_type in pipeline_events else 99)
    ]

    # ── 최근 오류 이벤트 5건 ─────────────────────────────────
    error_rows = (
        db.query(TraceEvent)
        .filter(
            TraceEvent.created_at >= since,
            TraceEvent.status == "error",
        )
        .order_by(TraceEvent.id.desc())
        .limit(5)
        .all()
    )
    recent_errors = [
        {
            "request_id": row.request_id,
            "event_type": row.event_type,
            "agent_id":   row.agent_id,
            "tool_id":    row.tool_id,
            "output_data": row.output_data,
            "ts":         row.created_at.isoformat() if row.created_at else None,
        }
        for row in error_rows
    ]

    return {
        "period_hours":       hours,
        "summary": {
            "total_requests":  total_requests,
            "completed_count": completed_count,
            "success_rate":    success_rate,
            "avg_latency_ms":  avg_latency_ms,
            "error_count":     error_count,
        },
        "intent_distribution": intent_distribution,
        "agent_stats":         agent_stats,
        "tool_stats":          tool_stats,
        "pipeline_latency":    pipeline_latency,
        "recent_errors":       recent_errors,
    }


# SQLAlchemy Boolean → Integer 캐스팅 헬퍼
from sqlalchemy import Integer as Integer_
