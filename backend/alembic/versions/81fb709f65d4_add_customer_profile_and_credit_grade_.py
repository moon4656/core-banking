"""add_customer_profile_and_credit_grade_rate

Revision ID: 81fb709f65d4
Revises: de36b12fd28e
Create Date: 2026-06-15 11:10:10.188866

"""
from alembic import op
import sqlalchemy as sa

revision = '81fb709f65d4'
down_revision = 'de36b12fd28e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'customer_profile',
        sa.Column('id', sa.Integer(), nullable=False, comment='PK'),
        sa.Column('customer_id', sa.String(length=100), nullable=False, comment='고객 고유 ID (예: CUSTOMER_001)'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='고객 이름'),
        sa.Column('credit_grade', sa.Integer(), nullable=False, comment='신용등급 1(최우량)~10(위험)'),
        sa.Column('annual_income', sa.Integer(), nullable=True, comment='연소득 (만원 단위)'),
        sa.Column('employment_type', sa.String(length=50), nullable=True, comment='직업유형: 직장인 / 자영업자 / 프리랜서'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='레코드 생성 일시 (UTC)'),
        sa.PrimaryKeyConstraint('id'),
        comment='대출 상담 고객 프로파일. 신용등급·연소득·직업유형을 저장하며 개인화 금리 조회에 활용된다.',
    )
    op.create_index(op.f('ix_customer_profile_id'), 'customer_profile', ['id'], unique=False)
    op.create_index(op.f('ix_customer_profile_customer_id'), 'customer_profile', ['customer_id'], unique=True)

    op.create_table(
        'credit_grade_rate',
        sa.Column('id', sa.Integer(), nullable=False, comment='PK'),
        sa.Column('product_type', sa.String(length=100), nullable=False, comment='대출 상품 유형 (예: 직장인 신용대출)'),
        sa.Column('credit_grade', sa.Integer(), nullable=False, comment='신용등급 1~10'),
        sa.Column('min_rate', sa.Float(), nullable=False, comment='최저 적용 금리 (%)'),
        sa.Column('max_rate', sa.Float(), nullable=False, comment='최고 적용 금리 (%)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='레코드 생성 일시 (UTC)'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_type', 'credit_grade', name='uq_credit_grade_rate'),
        comment='신용등급별 상품 적용 금리표. product_type x credit_grade 조합으로 min_rate/max_rate를 정의한다.',
    )
    op.create_index(op.f('ix_credit_grade_rate_id'), 'credit_grade_rate', ['id'], unique=False)
    op.create_index(op.f('ix_credit_grade_rate_product_type'), 'credit_grade_rate', ['product_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_credit_grade_rate_product_type'), table_name='credit_grade_rate')
    op.drop_index(op.f('ix_credit_grade_rate_id'), table_name='credit_grade_rate')
    op.drop_table('credit_grade_rate')
    op.drop_index(op.f('ix_customer_profile_customer_id'), table_name='customer_profile')
    op.drop_index(op.f('ix_customer_profile_id'), table_name='customer_profile')
    op.drop_table('customer_profile')
