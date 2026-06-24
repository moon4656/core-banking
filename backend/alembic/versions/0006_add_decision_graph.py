"""add decision graph tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "leader_decision_node",
        sa.Column("id",             sa.Integer(),     primary_key=True),
        sa.Column("request_id",     sa.String(100),   nullable=False),
        sa.Column("node_id",        sa.String(160),   nullable=False, unique=True),
        sa.Column("node_type",      sa.String(32),    nullable=False),
        sa.Column("node_label",     sa.String(128),   nullable=True),
        sa.Column("status",         sa.String(16),    nullable=False, server_default="SUCCESS"),
        sa.Column("sequence_order", sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("position_x",     sa.Float(),       nullable=True,  server_default="0"),
        sa.Column("position_y",     sa.Float(),       nullable=True,  server_default="0"),
        sa.Column("data",           JSONB(),          nullable=False, server_default="{}"),
        sa.Column("style",          JSONB(),          nullable=True,  server_default="{}"),
        sa.Column("duration_ms",    sa.Integer(),     nullable=True),
        sa.Column("created_at",     sa.DateTime(),    nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_ldn_request_id", "leader_decision_node", ["request_id"])
    op.create_index("idx_ldn_node_type",  "leader_decision_node", ["node_type"])
    op.create_index("idx_ldn_status",     "leader_decision_node", ["status"])

    op.create_table(
        "leader_decision_edge",
        sa.Column("id",             sa.Integer(),     primary_key=True),
        sa.Column("request_id",     sa.String(100),   nullable=False),
        sa.Column("edge_id",        sa.String(160),   nullable=False, unique=True),
        sa.Column("edge_type",      sa.String(32),    nullable=False),
        sa.Column("edge_label",     sa.String(64),    nullable=True),
        sa.Column("source_node_id", sa.String(160),   nullable=False),
        sa.Column("target_node_id", sa.String(160),   nullable=False),
        sa.Column("data",           JSONB(),          nullable=True, server_default="{}"),
        sa.Column("style",          JSONB(),          nullable=True, server_default="{}"),
        sa.Column("weight",         sa.Float(),       nullable=True, server_default="1.0"),
        sa.Column("created_at",     sa.DateTime(),    nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_lde_request_id",   "leader_decision_edge", ["request_id"])
    op.create_index("idx_lde_source_node",  "leader_decision_edge", ["source_node_id"])
    op.create_index("idx_lde_target_node",  "leader_decision_edge", ["target_node_id"])

    op.create_table(
        "leader_decision_review",
        sa.Column("id",                  sa.Integer(),     primary_key=True),
        sa.Column("request_id",          sa.String(100),   nullable=False, unique=True),
        sa.Column("reviewer_id",         sa.String(64),    nullable=True),
        sa.Column("status",              sa.String(16),    nullable=True,  server_default="PENDING"),
        sa.Column("overall_result",      sa.String(32),    nullable=True),
        sa.Column("intent_correct",      sa.Boolean(),     nullable=True),
        sa.Column("concept_complete",    sa.Boolean(),     nullable=True),
        sa.Column("agent_correct",       sa.Boolean(),     nullable=True),
        sa.Column("evidence_sufficient", sa.Boolean(),     nullable=True),
        sa.Column("answer_appropriate",  sa.Boolean(),     nullable=True),
        sa.Column("missing_concepts",    sa.JSON(),        nullable=True),
        sa.Column("wrong_agents",        sa.JSON(),        nullable=True),
        sa.Column("comment",             sa.Text(),        nullable=True),
        sa.Column("review_score",        sa.Float(),       nullable=True),
        sa.Column("reviewed_at",         sa.DateTime(),    nullable=True),
        sa.Column("created_at",          sa.DateTime(),    nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_ldr_request_id", "leader_decision_review", ["request_id"])
    op.create_index("idx_ldr_status",     "leader_decision_review", ["status"])


def downgrade():
    op.drop_index("idx_ldr_status",     table_name="leader_decision_review")
    op.drop_index("idx_ldr_request_id", table_name="leader_decision_review")
    op.drop_table("leader_decision_review")

    op.drop_index("idx_lde_target_node",  table_name="leader_decision_edge")
    op.drop_index("idx_lde_source_node",  table_name="leader_decision_edge")
    op.drop_index("idx_lde_request_id",   table_name="leader_decision_edge")
    op.drop_table("leader_decision_edge")

    op.drop_index("idx_ldn_status",     table_name="leader_decision_node")
    op.drop_index("idx_ldn_node_type",  table_name="leader_decision_node")
    op.drop_index("idx_ldn_request_id", table_name="leader_decision_node")
    op.drop_table("leader_decision_node")
