"""add_monitor_tables — Leader Agent 모니터링 mon_* 테이블 7개 신규 생성

Revision ID: 0014_add_monitor_tables
Revises: 0013_eval_agent_routing
Create Date: 2026-06-16

mon_agent_trace        : 요청 헤더 (루트 레코드)
mon_intent_analysis    : 의미분석 결과 (Tab 1)
mon_concept_detection  : Concept 탐지 (Tab 2)
mon_routing_decision   : Agent 라우팅 결정 (Tab 3)
mon_tool_execution     : Tool 실행 로그 (Tab 4)
mon_answer_sentence    : 최종 답변 문장별 근거 (Tab 5)
mon_gate_check         : Gate Rule 체크 결과
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0014_add_monitor_tables'
down_revision = '0013_eval_agent_routing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. mon_agent_trace ─────────────────────────────────────────────────
    op.create_table(
        'mon_agent_trace',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, unique=True, comment='요청 고유 ID'),
        sa.Column('user_id', sa.String(128), nullable=True, comment='요청 사용자 ID'),
        sa.Column('session_id', sa.String(128), nullable=True, comment='Redis Short Memory 세션 ID'),
        sa.Column('original_query', sa.Text(), nullable=False, comment='사용자 원본 질의'),
        sa.Column('normalized_query', sa.Text(), nullable=True, comment='정규화된 질의'),
        sa.Column('status', sa.String(20), nullable=False, server_default='processing',
                  comment='처리 상태: processing / completed / warning / blocked / failed'),
        sa.Column('total_latency_ms', sa.Integer(), nullable=True, comment='전체 처리 시간 (ms)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='Leader Agent 모니터링 요청 헤더. request_id 기준으로 mon_* 테이블 전체를 조인한다.',
    )
    op.create_index('ix_mon_agent_trace_request_id', 'mon_agent_trace', ['request_id'])
    op.create_index('ix_mon_agent_trace_user_id',    'mon_agent_trace', ['user_id'])
    op.create_index('ix_mon_agent_trace_created_at', 'mon_agent_trace', ['created_at'])

    # ── 2. mon_intent_analysis ─────────────────────────────────────────────
    op.create_table(
        'mon_intent_analysis',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, comment='요청 고유 ID'),
        sa.Column('primary_intent', sa.String(128), nullable=True,
                  comment='1차 의도 레이블 (예: loan_information_lookup)'),
        sa.Column('secondary_intents', JSONB(), nullable=True,
                  comment='2차 의도 목록 JSONB'),
        sa.Column('query_type', sa.String(64), nullable=True,
                  comment='질의 유형: single_topic / multi_topic'),
        sa.Column('needs_tool_execution', sa.Boolean(), nullable=False, server_default='false',
                  comment='Tool 실행 필요 여부'),
        sa.Column('needs_memory', sa.Boolean(), nullable=False, server_default='false',
                  comment='Short Memory 참조 필요 여부'),
        sa.Column('confidence', sa.Float(), nullable=True,
                  comment='의도 분석 신뢰도 (0.0~1.0)'),
        sa.Column('reason', sa.Text(), nullable=True, comment='의도 분류 판단 근거'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='Leader Agent 의도 분석 결과. 모니터링 Tab 1 데이터 소스.',
    )
    op.create_index('ix_mon_intent_analysis_request_id', 'mon_intent_analysis', ['request_id'])

    # ── 3. mon_concept_detection ───────────────────────────────────────────
    op.create_table(
        'mon_concept_detection',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, comment='요청 고유 ID'),
        sa.Column('source_text', sa.String(256), nullable=True,
                  comment="원문에서 Concept를 트리거한 표현 (예: '필요한 서류')"),
        sa.Column('concept_id', sa.String(128), nullable=True,
                  comment='탐지된 Concept ID'),
        sa.Column('concept_label', sa.String(256), nullable=True,
                  comment='Concept 사람 이름 (예: 필요서류)'),
        sa.Column('concept_type', sa.String(64), nullable=True,
                  comment='Concept 유형 (예: loan_product / rate / policy)'),
        sa.Column('confidence', sa.Float(), nullable=True,
                  comment='탐지 신뢰도 (0.0~1.0). 0.7 미만 → Gate 1 WARNING'),
        sa.Column('expanded_terms', JSONB(), nullable=True,
                  comment='Alias·유사어 확장 결과 목록 JSONB'),
        sa.Column('status', sa.String(20), nullable=False, server_default='normal',
                  comment='탐지 상태: normal / low_confidence'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='Concept 탐지 결과 행. confidence < 0.7이면 Gate 1 WARNING 트리거.',
    )
    op.create_index('ix_mon_concept_detection_request_id', 'mon_concept_detection', ['request_id'])
    op.create_index('ix_mon_concept_detection_concept_id', 'mon_concept_detection', ['concept_id'])

    # ── 4. mon_routing_decision ────────────────────────────────────────────
    op.create_table(
        'mon_routing_decision',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, comment='요청 고유 ID'),
        sa.Column('agent_name', sa.String(128), nullable=False,
                  comment='평가 대상 Agent 이름 (예: RATE_AGENT)'),
        sa.Column('selected', sa.Boolean(), nullable=False, server_default='false',
                  comment='최종 선택 여부'),
        sa.Column('related_concepts', JSONB(), nullable=True,
                  comment='선택 근거가 된 Concept ID 목록 JSONB'),
        sa.Column('reason', sa.Text(), nullable=True, comment='선택 또는 제외 사유'),
        sa.Column('routing_confidence', sa.Float(), nullable=True,
                  comment='라우팅 신뢰도 (0.0~1.0)'),
        sa.Column('execution_order', sa.Integer(), nullable=True,
                  comment='실행 순서 (selected=True일 때만 설정, 1부터 시작)'),
        sa.Column('status', sa.String(20), nullable=False, server_default='excluded',
                  comment='라우팅 상태: selected / excluded'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='Agent 선택·제외 결정 로그. selected_agents가 0개이면 Gate 2 BLOCKED.',
    )
    op.create_index('ix_mon_routing_decision_request_id', 'mon_routing_decision', ['request_id'])

    # ── 5. mon_tool_execution ──────────────────────────────────────────────
    op.create_table(
        'mon_tool_execution',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, comment='요청 고유 ID'),
        sa.Column('agent_name', sa.String(128), nullable=False,
                  comment='Tool을 호출한 Agent 이름'),
        sa.Column('tool_name', sa.String(128), nullable=False,
                  comment='실행된 Tool 이름 (예: MOCK_RATE_LOOKUP)'),
        sa.Column('tool_input', JSONB(), nullable=True,
                  comment='Tool 호출 입력값 JSONB (원본 파라미터)'),
        sa.Column('output_summary', sa.Text(), nullable=True,
                  comment='Tool 출력 요약 문자열 (UI 표시용)'),
        sa.Column('status', sa.String(20), nullable=False, server_default='success',
                  comment='실행 결과: success / failed / timeout'),
        sa.Column('latency_ms', sa.Integer(), nullable=True, comment='Tool 응답 시간 (ms)'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0',
                  comment='재시도 횟수'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='실패 시 오류 메시지'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='Tool 실행 1건 로그. tool_input JSONB·retry_count 포함.',
    )
    op.create_index('ix_mon_tool_execution_request_id', 'mon_tool_execution', ['request_id'])

    # ── 6. mon_answer_sentence ─────────────────────────────────────────────
    op.create_table(
        'mon_answer_sentence',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, comment='요청 고유 ID'),
        sa.Column('answer_sentence', sa.Text(), nullable=False,
                  comment='최종 답변 문장 (1문장 단위)'),
        sa.Column('source_agent', sa.String(128), nullable=True,
                  comment='문장 근거를 제공한 Agent 이름'),
        sa.Column('source_tool', sa.String(128), nullable=True,
                  comment='문장 근거를 제공한 Tool 이름'),
        sa.Column('evidence_summary', sa.Text(), nullable=True,
                  comment='근거 데이터 요약 (Tool output 핵심 내용)'),
        sa.Column('grounded', sa.Boolean(), nullable=False, server_default='true',
                  comment='근거 연결 여부. False이면 Gate 3 WARNING — Hallucination 가능성'),
        sa.Column('warning_message', sa.Text(), nullable=True,
                  comment='grounded=False일 때 경고 메시지'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='최종 답변 문장별 근거 추적. grounded=False이면 Gate 3 WARNING.',
    )
    op.create_index('ix_mon_answer_sentence_request_id', 'mon_answer_sentence', ['request_id'])

    # ── 7. mon_gate_check ──────────────────────────────────────────────────
    op.create_table(
        'mon_gate_check',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='PK'),
        sa.Column('request_id', sa.String(100), nullable=False, comment='요청 고유 ID'),
        sa.Column('gate_name', sa.String(64), nullable=False,
                  comment='Gate 식별자: concept_confidence / agent_routing / answer_grounding'),
        sa.Column('gate_type', sa.String(20), nullable=False,
                  comment='Gate 동작 유형: WARNING / BLOCK'),
        sa.Column('condition', sa.String(256), nullable=True,
                  comment='Gate 판단 조건 설명 (예: confidence < 0.7)'),
        sa.Column('result', sa.String(20), nullable=False, server_default='PASS',
                  comment='평가 결과: PASS / WARNING / BLOCKED'),
        sa.Column('severity', sa.String(20), nullable=True,
                  comment='심각도: info / warning / critical'),
        sa.Column('message', sa.Text(), nullable=True, comment='Gate 위반 시 표시할 메시지'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='레코드 생성 일시 (UTC)'),
        comment='Gate Rule 평가 결과. result: PASS / WARNING / BLOCKED.',
    )
    op.create_index('ix_mon_gate_check_request_id', 'mon_gate_check', ['request_id'])


def downgrade() -> None:
    op.drop_index('ix_mon_gate_check_request_id',         table_name='mon_gate_check')
    op.drop_index('ix_mon_answer_sentence_request_id',    table_name='mon_answer_sentence')
    op.drop_index('ix_mon_tool_execution_request_id',     table_name='mon_tool_execution')
    op.drop_index('ix_mon_routing_decision_request_id',   table_name='mon_routing_decision')
    op.drop_index('ix_mon_concept_detection_concept_id',  table_name='mon_concept_detection')
    op.drop_index('ix_mon_concept_detection_request_id',  table_name='mon_concept_detection')
    op.drop_index('ix_mon_intent_analysis_request_id',    table_name='mon_intent_analysis')
    op.drop_index('ix_mon_agent_trace_created_at',        table_name='mon_agent_trace')
    op.drop_index('ix_mon_agent_trace_user_id',           table_name='mon_agent_trace')
    op.drop_index('ix_mon_agent_trace_request_id',        table_name='mon_agent_trace')

    op.drop_table('mon_gate_check')
    op.drop_table('mon_answer_sentence')
    op.drop_table('mon_tool_execution')
    op.drop_table('mon_routing_decision')
    op.drop_table('mon_concept_detection')
    op.drop_table('mon_intent_analysis')
    op.drop_table('mon_agent_trace')
