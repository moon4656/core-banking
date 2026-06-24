"""add leader eval fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # leader_decision — 신규 컬럼 (모두 nullable)
    op.add_column("leader_decision", sa.Column("direct_concepts", sa.JSON(), nullable=True))
    op.add_column("leader_decision", sa.Column("expanded_concepts", sa.JSON(), nullable=True))
    op.add_column("leader_decision", sa.Column("ltm_turns", sa.Integer(), nullable=True))
    op.add_column("leader_decision", sa.Column("answer", sa.Text(), nullable=True))
    op.add_column("leader_decision", sa.Column("review_reason", sa.String(100), nullable=True))

    # evidence_reference — 출처 Agent 컬럼
    op.add_column("evidence_reference", sa.Column("agent_id", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("leader_decision", "direct_concepts")
    op.drop_column("leader_decision", "expanded_concepts")
    op.drop_column("leader_decision", "ltm_turns")
    op.drop_column("leader_decision", "answer")
    op.drop_column("leader_decision", "review_reason")
    op.drop_column("evidence_reference", "agent_id")
