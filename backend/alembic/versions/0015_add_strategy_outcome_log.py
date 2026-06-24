"""add_strategy_outcome_log — 재시도 전략 시도 결과 로그 테이블 추가

Revision ID: 0015_add_strategy_outcome_log
Revises: 0014_add_monitor_tables
Create Date: 2026-06-17

strategy_outcome_log:
  trigger_gate × strategy_name 기준 성공률 집계로 최적 재시도 전략을 학습한다.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision      = "0015_add_strategy_outcome_log"
down_revision = "0014_add_monitor_tables"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "strategy_outcome_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True,
                  comment="PK"),
        sa.Column("request_id", sa.String(100), nullable=False,
                  comment="요청 고유 ID (mon_agent_trace.request_id 논리 참조)"),
        sa.Column("trigger_gate", sa.String(64), nullable=False,
                  comment="트리거 Gate: tool_empty | tool_error | gate1_warn"),
        sa.Column("strategy_name", sa.String(64), nullable=False,
                  comment="적용 전략: remove_params | alt_api | expand_synonyms | rewrite_query"),
        sa.Column("api_id", sa.String(128), nullable=True,
                  comment="대상 API ID (tool retry 시); Gate 1 보강 시 NULL"),
        sa.Column("intent", sa.String(128), nullable=True,
                  comment="요청 의도 레이블 (예: INQUIRY)"),
        sa.Column("concept_ids", JSONB(), nullable=True,
                  comment="관련 Concept ID 목록 JSONB"),
        sa.Column("outcome", sa.String(20), nullable=True,
                  comment="결과: success | failed | no_change (update_outcome 호출 시 채워짐)"),
        sa.Column("confidence_after", sa.Float(), nullable=True,
                  comment="전략 적용 후 신뢰도 (0.0~1.0)"),
        sa.Column("latency_ms", sa.Integer(), nullable=True,
                  comment="전략 실행 소요 시간 (ms)"),
        sa.Column("error_detail", sa.Text(), nullable=True,
                  comment="실패 시 오류 메시지"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="레코드 생성 일시 (UTC)"),
        comment="Retry/보강 전략 시도 로그. trigger_gate×strategy_name 집계로 최선 전략 학습.",
    )
    op.create_index(
        "ix_strategy_outcome_log_request_id",
        "strategy_outcome_log", ["request_id"],
    )
    op.create_index(
        "ix_strategy_outcome_log_trigger_gate",
        "strategy_outcome_log", ["trigger_gate"],
    )
    op.create_index(
        "ix_strategy_outcome_log_created_at",
        "strategy_outcome_log", ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_outcome_log_created_at",   table_name="strategy_outcome_log")
    op.drop_index("ix_strategy_outcome_log_trigger_gate", table_name="strategy_outcome_log")
    op.drop_index("ix_strategy_outcome_log_request_id",   table_name="strategy_outcome_log")
    op.drop_table("strategy_outcome_log")
