"""add decision trace owner scope

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ai_decision_trace", sa.Column("owner_name", sa.String(length=100), nullable=True))
    op.add_column("ai_decision_trace", sa.Column("owner_role", sa.String(length=32), nullable=True))
    op.create_index("ix_ai_decision_trace_owner_name", "ai_decision_trace", ["owner_name"], unique=False)
    op.create_index("ix_ai_decision_trace_owner_role", "ai_decision_trace", ["owner_role"], unique=False)


def downgrade():
    op.drop_index("ix_ai_decision_trace_owner_role", table_name="ai_decision_trace")
    op.drop_index("ix_ai_decision_trace_owner_name", table_name="ai_decision_trace")
    op.drop_column("ai_decision_trace", "owner_role")
    op.drop_column("ai_decision_trace", "owner_name")
