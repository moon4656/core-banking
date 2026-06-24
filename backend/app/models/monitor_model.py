from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class MonAgentTrace(Base):
    """모니터링 요청 헤더. 요청 1건당 1행. 5개 상세 로그 테이블의 루트 레코드."""
    __tablename__ = "mon_agent_trace"
    __table_args__ = {"comment": "Leader Agent 모니터링 요청 헤더. request_id 기준으로 mon_* 테이블 전체를 조인한다."}

    id               = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id       = Column(String(100), unique=True, nullable=False, index=True, comment="요청 고유 ID")
    user_id          = Column(String(128), nullable=True, index=True, comment="요청 사용자 ID")
    session_id       = Column(String(128), nullable=True, index=True, comment="Redis Short Memory 세션 ID")
    original_query   = Column(Text, nullable=False, comment="사용자 원본 질의")
    normalized_query = Column(Text, nullable=True, comment="정규화된 질의")
    status           = Column(String(20), nullable=False, default="processing",
                              comment="처리 상태: processing / completed / warning / blocked / failed")
    total_latency_ms = Column(Integer, nullable=True, comment="전체 처리 시간 (ms)")
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class MonIntentAnalysis(Base):
    """의미분석 결과. 요청 1건당 1행. Tab 1 데이터 소스."""
    __tablename__ = "mon_intent_analysis"
    __table_args__ = {"comment": "Leader Agent 의도 분석 결과. primary_intent·confidence·근거를 컬럼으로 분리해 모니터링 Tab 1에서 직접 조회한다."}

    id                   = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id           = Column(String(100), nullable=False, index=True, comment="요청 고유 ID (FK 논리 참조 → mon_agent_trace.request_id)")
    primary_intent       = Column(String(128), nullable=True, comment="1차 의도 레이블 (예: loan_information_lookup)")
    secondary_intents    = Column(JSONB, nullable=True, default=list, comment="2차 의도 목록 JSONB (예: [\"interest_rate_lookup\"])")
    query_type           = Column(String(64), nullable=True, comment="질의 유형: single_topic / multi_topic")
    needs_tool_execution = Column(Boolean, nullable=False, default=False, comment="Tool 실행 필요 여부")
    needs_memory         = Column(Boolean, nullable=False, default=False, comment="Short Memory 참조 필요 여부")
    confidence           = Column(Float, nullable=True, comment="의도 분석 신뢰도 (0.0~1.0)")
    reason               = Column(Text, nullable=True, comment="의도 분류 판단 근거")
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class MonConceptDetection(Base):
    """Concept 탐지 결과. 탐지된 Concept 수만큼 행 생성. Tab 2 데이터 소스."""
    __tablename__ = "mon_concept_detection"
    __table_args__ = {"comment": "Concept 탐지 결과 행. source_text·confidence·expanded_terms 포함. confidence < 0.7이면 Gate 1 WARNING 트리거."}

    id             = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id     = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    source_text    = Column(String(256), nullable=True, comment="원문에서 Concept를 트리거한 표현 (예: '필요한 서류')")
    concept_id     = Column(String(128), nullable=True, index=True, comment="탐지된 Concept ID (예: CONCEPT_REQUIRED_DOCUMENT)")
    concept_label  = Column(String(256), nullable=True, comment="Concept 사람 이름 (예: 필요서류)")
    concept_type   = Column(String(64), nullable=True, comment="Concept 유형 (예: loan_product / rate / policy)")
    confidence     = Column(Float, nullable=True, comment="탐지 신뢰도 (0.0~1.0). 0.7 미만 → Gate 1 WARNING")
    expanded_terms = Column(JSONB, nullable=True, default=list, comment="Alias·유사어 확장 결과 목록 JSONB")
    status         = Column(String(20), nullable=False, default="normal",
                            comment="탐지 상태: normal / low_confidence")
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class MonRoutingDecision(Base):
    """Agent 라우팅 결정. 평가 대상 Agent 수만큼 행 생성 (선택·제외 모두 포함). Tab 3 데이터 소스."""
    __tablename__ = "mon_routing_decision"
    __table_args__ = {"comment": "Agent 선택·제외 결정 로그. selected=True/False 모두 저장해 제외 사유를 사후 추적한다. selected_agents가 0개이면 Gate 2 BLOCKED."}

    id                 = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id         = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    agent_name         = Column(String(128), nullable=False, comment="평가 대상 Agent 이름 (예: RATE_AGENT)")
    selected           = Column(Boolean, nullable=False, default=False, comment="최종 선택 여부")
    related_concepts   = Column(JSONB, nullable=True, default=list, comment="선택 근거가 된 Concept ID 목록 JSONB")
    reason             = Column(Text, nullable=True, comment="선택 또는 제외 사유")
    routing_confidence = Column(Float, nullable=True, comment="라우팅 신뢰도 (0.0~1.0)")
    execution_order    = Column(Integer, nullable=True, comment="실행 순서 (selected=True일 때만 설정, 1부터 시작)")
    status             = Column(String(20), nullable=False, default="excluded",
                                comment="라우팅 상태: selected / excluded")
    created_at         = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class MonToolExecution(Base):
    """Tool 실행 로그. 실행된 Tool 수만큼 행 생성. Tab 4 데이터 소스."""
    __tablename__ = "mon_tool_execution"
    __table_args__ = {"comment": "Tool 실행 1건 로그. tool_input JSONB·retry_count 포함. 실패 시 error_message 기록."}

    id             = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id     = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    agent_name     = Column(String(128), nullable=False, comment="Tool을 호출한 Agent 이름")
    tool_name      = Column(String(128), nullable=False, comment="실행된 Tool 이름 (예: MOCK_RATE_LOOKUP)")
    tool_input     = Column(JSONB, nullable=True, comment="Tool 호출 입력값 JSONB (원본 파라미터)")
    output_summary = Column(Text, nullable=True, comment="Tool 출력 요약 문자열 (UI 표시용)")
    status         = Column(String(20), nullable=False, default="success",
                            comment="실행 결과: success / failed / timeout")
    latency_ms     = Column(Integer, nullable=True, comment="Tool 응답 시간 (ms)")
    retry_count    = Column(Integer, nullable=False, default=0, comment="재시도 횟수")
    error_message  = Column(Text, nullable=True, comment="실패 시 오류 메시지")
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class MonAnswerSentence(Base):
    """최종 답변 문장 단위 근거 추적. 문장 수만큼 행 생성. Tab 5 데이터 소스."""
    __tablename__ = "mon_answer_sentence"
    __table_args__ = {"comment": "최종 답변의 문장별 근거 기록. grounded=False이면 Gate 3 WARNING. Hallucination 추적용."}

    id               = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id       = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    answer_sentence  = Column(Text, nullable=False, comment="최종 답변 문장 (1문장 단위)")
    source_agent     = Column(String(128), nullable=True, comment="문장 근거를 제공한 Agent 이름")
    source_tool      = Column(String(128), nullable=True, comment="문장 근거를 제공한 Tool 이름")
    evidence_summary = Column(Text, nullable=True, comment="근거 데이터 요약 (Tool output 핵심 내용)")
    grounded         = Column(Boolean, nullable=False, default=True,
                              comment="근거 연결 여부. False이면 Gate 3 WARNING — Hallucination 가능성")
    warning_message  = Column(Text, nullable=True, comment="grounded=False일 때 경고 메시지")
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class MonGateCheck(Base):
    """Gate Rule 체크 결과. 요청 1건당 Gate 수만큼 행 생성 (현재 3개). Gate 알림 영역 데이터 소스."""
    __tablename__ = "mon_gate_check"
    __table_args__ = {"comment": "Gate Rule 평가 결과 1행. gate_name: concept_confidence / agent_routing / answer_grounding. result: PASS / WARNING / BLOCKED."}

    id          = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id  = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    gate_name   = Column(String(64), nullable=False,
                         comment="Gate 식별자: concept_confidence / agent_routing / answer_grounding")
    gate_type   = Column(String(20), nullable=False,
                         comment="Gate 동작 유형: WARNING (경고 후 계속) / BLOCK (이후 단계 중단)")
    condition   = Column(String(256), nullable=True, comment="Gate 판단 조건 설명 (예: confidence < 0.7)")
    result      = Column(String(20), nullable=False, default="PASS",
                         comment="평가 결과: PASS / WARNING / BLOCKED")
    severity    = Column(String(20), nullable=True, comment="심각도: info / warning / critical")
    message     = Column(Text, nullable=True, comment="Gate 위반 시 표시할 메시지")
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")
