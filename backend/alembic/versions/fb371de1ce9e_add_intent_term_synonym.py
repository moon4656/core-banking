"""add_intent_term_synonym

Revision ID: fb371de1ce9e
Revises: c7a1fe85c0a0
Create Date: 2026-06-15 23:40:44.728204

"""
from alembic import op
import sqlalchemy as sa

revision = 'fb371de1ce9e'
down_revision = 'c7a1fe85c0a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'intent_term_synonym',
        sa.Column('id', sa.Integer(), nullable=False, comment='PK'),
        sa.Column('intent', sa.String(length=100), nullable=False, comment='의도 레이블 (예: RATE_MIN, RATE_MAX)'),
        sa.Column('term', sa.String(length=200), nullable=False, comment='동의어 문자열 (예: 최저, 가장 낮은)'),
        sa.Column('language', sa.String(length=20), nullable=False, comment='언어 코드'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='False이면 패턴 빌드에서 제외'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='레코드 생성 일시 (UTC)'),
        sa.PrimaryKeyConstraint('id'),
        comment='의도(intent) 감지용 동의어 사전.',
    )
    op.create_index('ix_intent_term_synonym_id', 'intent_term_synonym', ['id'], unique=False)
    op.create_index('ix_intent_term_synonym_intent', 'intent_term_synonym', ['intent'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_intent_term_synonym_intent', table_name='intent_term_synonym')
    op.drop_index('ix_intent_term_synonym_id', table_name='intent_term_synonym')
    op.drop_table('intent_term_synonym')
