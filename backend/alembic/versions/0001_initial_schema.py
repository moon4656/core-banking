"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_concept",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_id"),
    )
    op.create_index("ix_business_concept_concept_id", "business_concept", ["concept_id"])

    op.create_table(
        "business_term_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("alias", sa.String(200), nullable=False),
        sa.Column("language", sa.String(20), nullable=False, server_default="ko"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["business_concept.concept_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_term_alias_concept_id", "business_term_alias", ["concept_id"])

    op.create_table(
        "business_concept_relation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_concept_id", sa.String(100), nullable=False),
        sa.Column("target_concept_id", sa.String(100), nullable=False),
        sa.Column("relation_type", sa.String(100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_concept_id"], ["business_concept.concept_id"]),
        sa.ForeignKeyConstraint(["target_concept_id"], ["business_concept.concept_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_concept_relation_source", "business_concept_relation", ["source_concept_id"])
    op.create_index("ix_business_concept_relation_target", "business_concept_relation", ["target_concept_id"])

    op.create_table(
        "data_source_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("connection_info", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_data_source_catalog_source_id", "data_source_catalog", ["source_id"])

    op.create_table(
        "api_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("api_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False, server_default="GET"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("request_schema", sa.JSON(), nullable=True),
        sa.Column("response_schema", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_id"),
    )
    op.create_index("ix_api_catalog_api_id", "api_catalog", ["api_id"])

    op.create_table(
        "concept_data_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("field_path", sa.String(500), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["business_concept.concept_id"]),
        sa.ForeignKeyConstraint(["source_id"], ["data_source_catalog.source_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_concept_data_mapping_concept_id", "concept_data_mapping", ["concept_id"])

    op.create_table(
        "concept_api_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("api_id", sa.String(100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["business_concept.concept_id"]),
        sa.ForeignKeyConstraint(["api_id"], ["api_catalog.api_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_concept_api_mapping_concept_id", "concept_api_mapping", ["concept_id"])

    op.create_table(
        "agent_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )
    op.create_index("ix_agent_catalog_agent_id", "agent_catalog", ["agent_id"])

    op.create_table(
        "agent_concept_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_catalog.agent_id"]),
        sa.ForeignKeyConstraint(["concept_id"], ["business_concept.concept_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_concept_mapping_agent_id", "agent_concept_mapping", ["agent_id"])
    op.create_index("ix_agent_concept_mapping_concept_id", "agent_concept_mapping", ["concept_id"])

    op.create_table(
        "trace_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("tool_id", sa.String(100), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="success"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trace_event_request_id", "trace_event", ["request_id"])

    op.create_table(
        "evidence_reference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_id", sa.String(100), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_reference_request_id", "evidence_reference", ["request_id"])


def downgrade() -> None:
    op.drop_table("evidence_reference")
    op.drop_table("trace_event")
    op.drop_table("agent_concept_mapping")
    op.drop_table("agent_catalog")
    op.drop_table("concept_api_mapping")
    op.drop_table("concept_data_mapping")
    op.drop_table("api_catalog")
    op.drop_table("data_source_catalog")
    op.drop_table("business_concept_relation")
    op.drop_table("business_term_alias")
    op.drop_table("business_concept")
