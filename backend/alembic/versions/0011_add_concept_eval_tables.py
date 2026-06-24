"""add_concept_eval_tables

Revision ID: 0011_concept_eval
Revises: fb371de1ce9e
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0011_concept_eval'
down_revision = 'fb371de1ce9e'
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

    op.create_table(
        'concept_eval_run',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('run_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('run_type', sa.String(20), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('total_queries', sa.Integer(), nullable=False),
        sa.Column('avg_f1', sa.Float(), nullable=True),
        sa.Column('overall_grade', sa.String(2), nullable=False),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id'),
    )
    op.create_index('ix_concept_eval_run_run_id', 'concept_eval_run', ['run_id'])

    op.create_table(
        'concept_eval_item',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('expected_concepts', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('detected_concepts', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('true_positive', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('false_positive', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('false_negative', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('recall', sa.Float(), nullable=True),
        sa.Column('f1_score', sa.Float(), nullable=True),
        sa.Column('grade', sa.String(2), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['concept_eval_run.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_concept_eval_item_run_id', 'concept_eval_item', ['run_id'])


def downgrade() -> None:
    op.drop_index('ix_concept_eval_item_run_id', table_name='concept_eval_item')
    op.drop_table('concept_eval_item')
    op.drop_index('ix_concept_eval_run_run_id', table_name='concept_eval_run')
    op.drop_table('concept_eval_run')
    op.drop_table('concept_eval_custom_query')
