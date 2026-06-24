"""add_notification_rule_and_log

Revision ID: fc9637327979
Revises: 81fb709f65d4
Create Date: 2026-06-15 12:44:37.886513

"""
from alembic import op
import sqlalchemy as sa

revision = 'fc9637327979'
down_revision = '81fb709f65d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notification_rule',
        sa.Column('id', sa.Integer(), nullable=False, comment='PK'),
        sa.Column('rule_id', sa.String(length=100), nullable=False, comment='규칙 고유 ID (예: RULE_RATE_CHANGE)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='규칙 이름'),
        sa.Column('trigger_type', sa.String(length=100), nullable=False, comment='트리거 유형: RATE_CHANGE / MATURITY / OVERDUE / LIMIT_USAGE / GRADE_UP'),
        sa.Column('channel', sa.String(length=50), nullable=False, comment='알림 채널: PUSH / SMS / EMAIL / IN_APP'),
        sa.Column('message_template', sa.Text(), nullable=False, comment='알림 메시지 템플릿'),
        sa.Column('threshold', sa.Float(), nullable=True, comment='트리거 임계값'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='False이면 이 규칙은 실행하지 않음'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='레코드 생성 일시 (UTC)'),
        sa.PrimaryKeyConstraint('id'),
        comment='알림 발송 규칙 정의.',
    )
    op.create_index(op.f('ix_notification_rule_id'), 'notification_rule', ['id'], unique=False)
    op.create_index(op.f('ix_notification_rule_rule_id'), 'notification_rule', ['rule_id'], unique=True)

    op.create_table(
        'notification_log',
        sa.Column('id', sa.Integer(), nullable=False, comment='PK'),
        sa.Column('rule_id', sa.String(length=100), nullable=True, comment='FK → notification_rule.rule_id'),
        sa.Column('customer_id', sa.String(length=100), nullable=True, comment='알림 대상 고객 ID'),
        sa.Column('channel', sa.String(length=50), nullable=False, comment='실제 발송 채널'),
        sa.Column('message', sa.Text(), nullable=False, comment='실제 발송된 메시지 내용'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='발송 상태: SENT / FAILED / PENDING'),
        sa.Column('trigger_data', sa.JSON(), nullable=True, comment='트리거 발생 시 데이터 JSON'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='발송 일시 (UTC)'),
        sa.ForeignKeyConstraint(['rule_id'], ['notification_rule.rule_id']),
        sa.PrimaryKeyConstraint('id'),
        comment='알림 발송 이력.',
    )
    op.create_index(op.f('ix_notification_log_id'), 'notification_log', ['id'], unique=False)
    op.create_index(op.f('ix_notification_log_rule_id'), 'notification_log', ['rule_id'], unique=False)
    op.create_index(op.f('ix_notification_log_customer_id'), 'notification_log', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_log_customer_id'), table_name='notification_log')
    op.drop_index(op.f('ix_notification_log_rule_id'), table_name='notification_log')
    op.drop_index(op.f('ix_notification_log_id'), table_name='notification_log')
    op.drop_table('notification_log')
    op.drop_index(op.f('ix_notification_rule_rule_id'), table_name='notification_rule')
    op.drop_index(op.f('ix_notification_rule_id'), table_name='notification_rule')
    op.drop_table('notification_rule')
