"""add leader_decision table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leader_decision",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("detected_intent", sa.String(50), nullable=True),
        sa.Column("detected_concepts", sa.JSON(), nullable=True),
        sa.Column("selected_agents", sa.JSON(), nullable=True),
        sa.Column("reasoning", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("total_steps", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("memory_turns", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leader_decision_request_id", "leader_decision", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_leader_decision_request_id", table_name="leader_decision")
    op.drop_table("leader_decision")
