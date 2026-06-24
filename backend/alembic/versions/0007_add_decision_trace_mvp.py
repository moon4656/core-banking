"""add decision trace mvp tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_decision_trace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=True),
        sa.Column("request_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("memory_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("intent_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("latency", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_decision_trace_request_id", "ai_decision_trace", ["request_id"], unique=True)
    op.create_index("ix_ai_decision_trace_session_id", "ai_decision_trace", ["session_id"], unique=False)

    op.create_table(
        "ai_concept_detection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("concept_id", sa.String(length=100), nullable=False),
        sa.Column("detection_stage", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("source_terms", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("relation_path", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_concept_detection_request_id", "ai_concept_detection", ["request_id"], unique=False)
    op.create_index("ix_ai_concept_detection_concept_id", "ai_concept_detection", ["concept_id"], unique=False)

    op.create_table(
        "ai_agent_selection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("matched_concepts", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_agent_selection_request_id", "ai_agent_selection", ["request_id"], unique=False)
    op.create_index("ix_ai_agent_selection_agent_id", "ai_agent_selection", ["agent_id"], unique=False)

    op.create_table(
        "ai_tool_execution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("tool_code", sa.String(length=100), nullable=False),
        sa.Column("concept_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_tool_execution_request_id", "ai_tool_execution", ["request_id"], unique=False)
    op.create_index("ix_ai_tool_execution_agent_id", "ai_tool_execution", ["agent_id"], unique=False)
    op.create_index("ix_ai_tool_execution_tool_code", "ai_tool_execution", ["tool_code"], unique=False)

    op.create_table(
        "ai_reranking_trace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("criteria_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("selected_evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_reranking_trace_request_id", "ai_reranking_trace", ["request_id"], unique=True)

    op.create_table(
        "ai_final_answer_trace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answer_summary", sa.Text(), nullable=True),
        sa.Column("used_evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("grounding_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_final_answer_trace_request_id", "ai_final_answer_trace", ["request_id"], unique=True)


def downgrade():
    op.drop_index("ix_ai_final_answer_trace_request_id", table_name="ai_final_answer_trace")
    op.drop_table("ai_final_answer_trace")

    op.drop_index("ix_ai_reranking_trace_request_id", table_name="ai_reranking_trace")
    op.drop_table("ai_reranking_trace")

    op.drop_index("ix_ai_tool_execution_tool_code", table_name="ai_tool_execution")
    op.drop_index("ix_ai_tool_execution_agent_id", table_name="ai_tool_execution")
    op.drop_index("ix_ai_tool_execution_request_id", table_name="ai_tool_execution")
    op.drop_table("ai_tool_execution")

    op.drop_index("ix_ai_agent_selection_agent_id", table_name="ai_agent_selection")
    op.drop_index("ix_ai_agent_selection_request_id", table_name="ai_agent_selection")
    op.drop_table("ai_agent_selection")

    op.drop_index("ix_ai_concept_detection_concept_id", table_name="ai_concept_detection")
    op.drop_index("ix_ai_concept_detection_request_id", table_name="ai_concept_detection")
    op.drop_table("ai_concept_detection")

    op.drop_index("ix_ai_decision_trace_session_id", table_name="ai_decision_trace")
    op.drop_index("ix_ai_decision_trace_request_id", table_name="ai_decision_trace")
    op.drop_table("ai_decision_trace")
