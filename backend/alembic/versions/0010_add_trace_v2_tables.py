"""add trace v2 tables (Section 13)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-15

Section 13의 10개 Trace v2 테이블 중 기존 MVP 마이그레이션(0007)에서
생성되지 않은 5개 테이블을 추가한다.

기존 테이블 (0007 생성, 정수 PK + request_id 방식):
    ai_decision_trace, ai_concept_detection, ai_agent_selection,
    ai_tool_execution, ai_final_answer_trace  (→ 유지)

신규 추가 테이블 (UUID PK + trace_id FK 방식):
    ai_trace_event        — 최상위 요청 단위 (모든 v2 테이블의 루트 FK)
    ai_evidence_trace     — Evidence 수집 기록
    ai_answer_slot_ranking — Answer Slot별 Evidence 순위
    ai_validation_trace   — Validation 결과 (감사/컴플라이언스)
    ai_memory_save_decision — Memory 저장 판단 기록
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. ai_trace_event ──────────────────────────────────────────────
    # 모든 v2 Trace 테이블의 최상위 참조 키 (요청 단위)
    op.create_table(
        "ai_trace_event",
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("request_id", sa.String(64), nullable=False, unique=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("user_query_masked", sa.Text(), nullable=True),
        sa.Column("intent_name", sa.String(64), nullable=True),
        sa.Column(
            "intent_confidence",
            sa.Numeric(precision=4, scale=3),
            nullable=True,
        ),
        sa.Column("execution_strategy", sa.String(16), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "final_status",
            sa.String(16),
            nullable=False,
            server_default="SUCCESS",
        ),
        sa.Column(
            "risk_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("schema_version", sa.String(8), nullable=True, server_default="v2.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "final_status IN ('SUCCESS','PARTIAL','FAILED','FALLBACK')",
            name="ck_ai_trace_event_status",
        ),
    )
    op.create_index("idx_trace_event_session",  "ai_trace_event", ["session_id"])
    op.create_index("idx_trace_event_created",  "ai_trace_event", ["created_at"])
    op.create_index("idx_trace_event_request",  "ai_trace_event", ["request_id"], unique=True)

    # ── 2. ai_evidence_trace ───────────────────────────────────────────
    # Evidence 수집 기록 (Tool 실행 결과 품질/신뢰도 점수)
    op.create_table(
        "ai_evidence_trace",
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_trace_event.trace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool_exec_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_tool",  sa.String(64), nullable=False),
        sa.Column("source_agent", sa.String(64), nullable=False),
        sa.Column(
            "data_quality_score",
            sa.Numeric(precision=4, scale=3),
            nullable=True,
        ),
        sa.Column(
            "slot_relevance_score",
            sa.Numeric(precision=4, scale=3),
            nullable=True,
        ),
        sa.Column(
            "latency_bonus",
            sa.Numeric(precision=4, scale=3),
            nullable=True,
        ),
        sa.Column(
            "final_score",
            sa.Numeric(precision=4, scale=3),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "raw_content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_evidence_trace_trace",  "ai_evidence_trace", ["trace_id"])
    op.create_index("idx_evidence_score",        "ai_evidence_trace", ["final_score"])

    # ── 3. ai_answer_slot_ranking ──────────────────────────────────────
    # Answer Slot별 Evidence 순위 (복합 질문 처리 결과 가시화)
    op.create_table(
        "ai_answer_slot_ranking",
        sa.Column(
            "slot_rank_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_trace_event.trace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot_id",    sa.String(32), nullable=False),
        sa.Column("slot_name",  sa.String(64), nullable=False),
        sa.Column("question_part", sa.Text(), nullable=True),
        sa.Column(
            "answer_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "candidate_evidences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "selected_evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_evidence_trace.evidence_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "supporting_evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("selection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_slot_rank_trace", "ai_answer_slot_ranking", ["trace_id"])

    # ── 4. ai_validation_trace ─────────────────────────────────────────
    # Validation 결과 (10개 체크 항목, 감사/컴플라이언스 목적)
    op.create_table(
        "ai_validation_trace",
        sa.Column(
            "validation_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_trace_event.trace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("check_name",  sa.String(64), nullable=False),
        sa.Column("passed",      sa.Boolean(),  nullable=False),
        sa.Column(
            "severity",
            sa.String(16),
            nullable=True,
        ),
        sa.Column("detail",       sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "severity IN ('info','warn','error')",
            name="ck_ai_validation_severity",
        ),
    )
    op.create_index("idx_validation_trace",  "ai_validation_trace", ["trace_id"])
    op.create_index(
        "idx_validation_failed",
        "ai_validation_trace",
        ["trace_id", "passed"],
        postgresql_where=sa.text("passed = false"),
    )

    # ── 5. ai_memory_save_decision ─────────────────────────────────────
    # Memory 저장 판단 기록 (개인정보 처리 감사 목적)
    op.create_table(
        "ai_memory_save_decision",
        sa.Column(
            "mem_decision_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_trace_event.trace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("short_memory_saved", sa.Boolean(), nullable=False),
        sa.Column("short_memory_reason", sa.Text(), nullable=True),
        sa.Column("long_term_saved",     sa.Boolean(), nullable=False),
        sa.Column("long_term_reason",    sa.Text(), nullable=True),
        sa.Column("long_term_content",   sa.Text(), nullable=True),
        sa.Column(
            "sensitive_detected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "masking_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "masking_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "user_consent_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_mem_decision_trace", "ai_memory_save_decision", ["trace_id"])


def downgrade():
    # 역순 삭제 — FK 의존성 순서 준수
    op.drop_index("idx_mem_decision_trace", table_name="ai_memory_save_decision")
    op.drop_table("ai_memory_save_decision")

    op.drop_index("idx_validation_failed", table_name="ai_validation_trace")
    op.drop_index("idx_validation_trace",  table_name="ai_validation_trace")
    op.drop_table("ai_validation_trace")

    op.drop_index("idx_slot_rank_trace", table_name="ai_answer_slot_ranking")
    op.drop_table("ai_answer_slot_ranking")

    op.drop_index("idx_evidence_score",       table_name="ai_evidence_trace")
    op.drop_index("idx_evidence_trace_trace",  table_name="ai_evidence_trace")
    op.drop_table("ai_evidence_trace")

    op.drop_index("idx_trace_event_request",  table_name="ai_trace_event")
    op.drop_index("idx_trace_event_created",  table_name="ai_trace_event")
    op.drop_index("idx_trace_event_session",  table_name="ai_trace_event")
    op.drop_table("ai_trace_event")
