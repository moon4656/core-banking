"""add_concept_eval_custom_query

Revision ID: 0012_eval_custom_query
Revises: 0011_concept_eval
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0012_eval_custom_query'
down_revision = '0011_concept_eval'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'concept_eval_custom_query',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('expected_concepts', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('concept_eval_custom_query')
