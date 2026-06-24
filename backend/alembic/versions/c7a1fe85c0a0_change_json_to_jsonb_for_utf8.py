"""change_json_to_jsonb_for_utf8

Revision ID: c7a1fe85c0a0
Revises: fc9637327979
Create Date: 2026-06-15 14:26:45.501577

JSON 컬럼을 JSONB로 변환 — PostgreSQL JSONB는 \\u 이스케이프 없이
UTF-8 직접 저장하므로 DBeaver에서 한글이 정상 표시된다.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7a1fe85c0a0'
down_revision = 'fc9637327979'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agent_catalog ─────────────────────────────────────────────
    op.alter_column(
        'agent_catalog', 'capabilities',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── api_catalog ───────────────────────────────────────────────
    op.alter_column(
        'api_catalog', 'request_schema',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'api_catalog', 'response_schema',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── data_source_catalog ───────────────────────────────────────
    op.alter_column(
        'data_source_catalog', 'connection_info',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── evidence_reference ────────────────────────────────────────
    op.alter_column(
        'evidence_reference', 'content',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'evidence_reference', 'quality_flags',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'evidence_reference', 'related_evidence_ids',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── leader_decision ───────────────────────────────────────────
    op.alter_column(
        'leader_decision', 'detected_concepts',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'leader_decision', 'direct_concepts',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'leader_decision', 'expanded_concepts',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'leader_decision', 'selected_agents',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'leader_decision', 'reasoning',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── leader_decision_review ────────────────────────────────────
    op.alter_column(
        'leader_decision_review', 'missing_concepts',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'leader_decision_review', 'wrong_agents',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── notification_log ─────────────────────────────────────────
    op.alter_column(
        'notification_log', 'trigger_data',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── trace_event ──────────────────────────────────────────────
    op.alter_column(
        'trace_event', 'input_data',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'trace_event', 'output_data',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )

    # ── long_term_memory ─────────────────────────────────────────
    op.alter_column(
        'long_term_memory', 'detected_concepts',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        'long_term_memory', 'keywords',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )


def downgrade() -> None:
    for tbl, col in [
        ('long_term_memory', 'keywords'),
        ('long_term_memory', 'detected_concepts'),
        ('trace_event', 'output_data'),
        ('trace_event', 'input_data'),
        ('notification_log', 'trigger_data'),
        ('leader_decision_review', 'wrong_agents'),
        ('leader_decision_review', 'missing_concepts'),
        ('leader_decision', 'reasoning'),
        ('leader_decision', 'selected_agents'),
        ('leader_decision', 'expanded_concepts'),
        ('leader_decision', 'direct_concepts'),
        ('leader_decision', 'detected_concepts'),
        ('evidence_reference', 'related_evidence_ids'),
        ('evidence_reference', 'quality_flags'),
        ('evidence_reference', 'content'),
        ('data_source_catalog', 'connection_info'),
        ('api_catalog', 'response_schema'),
        ('api_catalog', 'request_schema'),
        ('agent_catalog', 'capabilities'),
    ]:
        op.alter_column(
            tbl, col,
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=postgresql.JSON(astext_type=sa.Text()),
            existing_nullable=True,
        )
