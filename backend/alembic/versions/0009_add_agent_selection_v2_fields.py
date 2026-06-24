"""add v2 fields to ai_agent_selection

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ai_agent_selection", sa.Column("role", sa.String(length=100), nullable=True))
    op.add_column("ai_agent_selection", sa.Column("execution_mode", sa.String(length=50), nullable=True))
    op.add_column(
        "ai_agent_selection",
        sa.Column(
            "tools_assigned",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "ai_agent_selection",
        sa.Column(
            "decision_rule_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade():
    op.drop_column("ai_agent_selection", "decision_rule_ids")
    op.drop_column("ai_agent_selection", "tools_assigned")
    op.drop_column("ai_agent_selection", "execution_mode")
    op.drop_column("ai_agent_selection", "role")
