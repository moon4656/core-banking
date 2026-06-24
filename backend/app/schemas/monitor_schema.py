"""monitor_schema.py — Leader Agent 모니터링 API 응답 스키마

mon_* 테이블 조회 결과를 프론트엔드 모니터링 화면용으로 직렬화한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.config import settings


# ── 공통 ORM 모드 베이스 ───────────────────────────────────────────────────

class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── 트레이스 목록 아이템 ──────────────────────────────────────────────────

class MonTraceListItem(_ORM):
    request_id: str
    user_id: str | None = None
    session_id: str | None = None
    original_query: str | None = None
    status: str
    total_latency_ms: int | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        try:
            value = value.astimezone(ZoneInfo(settings.APP_TIMEZONE))
        except Exception:
            value = value.astimezone(timezone.utc)
        return value.isoformat()


class MonTraceListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[MonTraceListItem]


# ── 트레이스 상세: 7개 섹션 ──────────────────────────────────────────────

class MonIntentDetail(_ORM):
    primary_intent: str | None = None
    secondary_intents: list[str] = Field(default_factory=list)
    query_type: str | None = None
    needs_tool_execution: bool = False
    needs_memory: bool = False
    confidence: float | None = None
    reason: str | None = None


class MonConceptDetail(_ORM):
    concept_id: str | None = None
    concept_label: str | None = None
    concept_type: str | None = None
    source_text: str | None = None
    confidence: float | None = None
    expanded_terms: list[str] = Field(default_factory=list)
    status: str | None = None  # normal | low_confidence


class MonRoutingDetail(_ORM):
    agent_name: str | None = None
    selected: bool = False
    related_concepts: list[str] = Field(default_factory=list)
    reason: str | None = None
    routing_confidence: float | None = None
    execution_order: int | None = None
    status: str | None = None  # selected | excluded


class MonToolDetail(_ORM):
    agent_name: str | None = None
    tool_name: str | None = None
    tool_input: dict | None = None
    output_summary: str | None = None
    status: str | None = None
    latency_ms: int | None = None
    retry_count: int = 0
    error_message: str | None = None


class MonSentenceDetail(_ORM):
    answer_sentence: str | None = None
    source_agent: str | None = None
    source_tool: str | None = None
    evidence_summary: str | None = None
    grounded: bool = True
    warning_message: str | None = None


class MonGateDetail(_ORM):
    gate_name: str | None = None
    gate_type: str | None = None
    condition: str | None = None
    result: str | None = None
    severity: str | None = None
    message: str | None = None


class MonTraceDetailResponse(BaseModel):
    """request_id 하나에 대한 7개 mon_* 테이블 전체 조합."""
    trace: MonTraceListItem
    intent: MonIntentDetail | None = None
    concepts: list[MonConceptDetail] = Field(default_factory=list)
    routing: list[MonRoutingDetail] = Field(default_factory=list)
    tools: list[MonToolDetail] = Field(default_factory=list)
    sentences: list[MonSentenceDetail] = Field(default_factory=list)
    gates: list[MonGateDetail] = Field(default_factory=list)


# ── Gate 전용 응답 ─────────────────────────────────────────────────────────

class MonGatesResponse(BaseModel):
    """request_id의 Gate 체크 결과만 반환한다."""
    request_id: str
    overall_status: str
    gates: list[MonGateDetail] = Field(default_factory=list)
