"""enhance evidence_reference: confidence scoring + evidence linking

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 신뢰도 점수 상세 컬럼 추가
    op.add_column("evidence_reference", sa.Column("data_quality_score",     sa.Float(),   nullable=True))
    op.add_column("evidence_reference", sa.Column("intent_relevance_score", sa.Float(),   nullable=True))
    op.add_column("evidence_reference", sa.Column("response_latency_ms",    sa.Integer(), nullable=True))
    op.add_column("evidence_reference", sa.Column("item_count",             sa.Integer(), nullable=True))
    op.add_column("evidence_reference", sa.Column("quality_flags",          sa.JSON(),    nullable=True))
    # 근거 간 연결 컬럼 추가
    op.add_column("evidence_reference", sa.Column("related_evidence_ids",   sa.JSON(),    nullable=True))


def downgrade() -> None:
    op.drop_column("evidence_reference", "related_evidence_ids")
    op.drop_column("evidence_reference", "quality_flags")
    op.drop_column("evidence_reference", "item_count")
    op.drop_column("evidence_reference", "response_latency_ms")
    op.drop_column("evidence_reference", "intent_relevance_score")
    op.drop_column("evidence_reference", "data_quality_score")
