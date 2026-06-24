"""add long_term_memory table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "long_term_memory",
        sa.Column("id",                sa.Integer(),     nullable=False),
        sa.Column("session_id",        sa.String(100),   nullable=False),
        sa.Column("user_id",           sa.String(100),   nullable=True),
        sa.Column("turn_index",        sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("intent",            sa.String(50),    nullable=True),
        sa.Column("detected_concepts", sa.JSON(),        nullable=True),
        sa.Column("keywords",          sa.JSON(),        nullable=True),
        sa.Column("question_summary",  sa.Text(),        nullable=True),
        sa.Column("answer_summary",    sa.Text(),        nullable=True),
        sa.Column("created_at",        sa.DateTime(),    nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_long_term_memory_id",         "long_term_memory", ["id"],         unique=False)
    op.create_index("ix_long_term_memory_session_id", "long_term_memory", ["session_id"], unique=False)
    op.create_index("ix_long_term_memory_user_id",    "long_term_memory", ["user_id"],    unique=False)


def downgrade() -> None:
    op.drop_index("ix_long_term_memory_user_id",    table_name="long_term_memory")
    op.drop_index("ix_long_term_memory_session_id", table_name="long_term_memory")
    op.drop_index("ix_long_term_memory_id",         table_name="long_term_memory")
    op.drop_table("long_term_memory")
