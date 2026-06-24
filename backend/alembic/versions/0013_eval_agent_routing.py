"""eval_agent_routing — expected_concepts → expected_agents, add routed_agents

Revision ID: 0013_eval_agent_routing
Revises: 0012_eval_custom_query
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0013_eval_agent_routing'
down_revision = '0012_eval_custom_query'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # concept_eval_custom_query: expected_concepts → expected_agents
    op.alter_column('concept_eval_custom_query', 'expected_concepts',
                    new_column_name='expected_agents')

    # concept_eval_item: expected_concepts → expected_agents
    op.alter_column('concept_eval_item', 'expected_concepts',
                    new_column_name='expected_agents')

    # concept_eval_item: routed_agents 컬럼 추가
    op.add_column('concept_eval_item',
                  sa.Column('routed_agents', postgresql.ARRAY(sa.String()),
                            nullable=True, server_default='{}'))

    # nullable=False로 변경
    op.alter_column('concept_eval_item', 'routed_agents', nullable=False)


def downgrade() -> None:
    op.drop_column('concept_eval_item', 'routed_agents')
    op.alter_column('concept_eval_item', 'expected_agents',
                    new_column_name='expected_concepts')
    op.alter_column('concept_eval_custom_query', 'expected_agents',
                    new_column_name='expected_concepts')
