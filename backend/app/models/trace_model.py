from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
JSON = JSONB  # 모든 JSON 컬럼을 JSONB로 통일 — \u 이스케이프 없이 UTF-8 직접 저장

from app.core.database import Base


class LeaderDecision(Base):
    __tablename__ = "leader_decision"
    __table_args__ = {"comment": "Leader Agent 라우팅 판단 감사 로그. 요청 1건당 1행을 기록하며 AI 설명 가능성(Explainability)·규정 준수(Compliance) 요구사항을 충족한다. request_id로 TraceEvent와 조인해 전체 처리 흐름을 추적할 수 있다."}

    id                 = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id         = Column(String(100), nullable=False, index=True, comment="요청 고유 ID (TraceEvent와 공유)")
    detected_intent    = Column(String(50), nullable=True, comment="LLM이 분류한 의도: INQUIRY / COMPARISON / RECOMMENDATION / APPLICATION / OTHER")
    detected_concepts  = Column(JSON, nullable=True, comment="온톨로지 확장 후 최종 concept 목록 (예: [\"CONCEPT_INTEREST_RATE\"])")
    direct_concepts    = Column(JSON, nullable=True, comment="키워드 직접 매칭으로 탐지된 concept 목록")
    expanded_concepts  = Column(JSON, nullable=True, comment="온톨로지 관계 확장으로 추가된 concept 목록")
    selected_agents    = Column(JSON, nullable=True, comment="라우팅된 Agent ID 목록 (예: [\"RATE_AGENT\"])")
    reasoning          = Column(JSON, nullable=True, comment="intent_data 전체 JSON — LLM 분류 근거")
    confidence_score   = Column(Float, default=1.0, nullable=True, comment="라우팅 신뢰도 (성공한 API 결과 수 / 전체 API 수)")
    total_steps        = Column(Integer, default=0, nullable=True, comment="생성된 ExecutionStep 수")
    memory_turns       = Column(Integer, default=0, nullable=True, comment="Short Memory에서 로드한 대화 턴 수")
    ltm_turns          = Column(Integer, default=0, nullable=True, comment="Long-Term Memory에서 로드한 턴 수")
    answer             = Column(Text, nullable=True, comment="최종 LLM 생성 답변 전문")
    review_reason      = Column(String(100), nullable=True, comment="검토 필요 원인 코드 (NEEDS_REVIEW / FAIL 등)")
    created_at         = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class TraceEvent(Base):
    __tablename__ = "trace_event"
    __table_args__ = {"comment": "요청 처리 단계별 이벤트 로그. request_id로 단일 요청의 전체 처리 흐름을 재현할 수 있다. 디버깅·성능 분석·감사(Audit)에 활용하며, 요청 1건당 여러 행이 기록된다."}

    id          = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id  = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    event_type  = Column(String(100), nullable=False, comment="이벤트 유형: REQUEST_RECEIVED / MEMORY_LOADED / INTENT_ANALYZED / CONCEPT_DETECTED / AGENT_SELECTED / PLAN_CREATED / RESULTS_RERANKED / TOOL_INVOKED / RESPONSE_COMPLETED")
    agent_id    = Column(String(100), nullable=True, comment="이벤트를 발생시킨 Agent ID (해당 없으면 NULL)")
    tool_id     = Column(String(100), nullable=True, comment="이벤트와 연관된 Tool ID (해당 없으면 NULL)")
    input_data  = Column(JSON, nullable=True, comment="해당 단계의 입력값 JSON")
    output_data = Column(JSON, nullable=True, comment="해당 단계의 출력값 JSON")
    status      = Column(String(50), nullable=False, default="success", comment="처리 결과: success / error")
    duration_ms = Column(Integer, nullable=True, comment="해당 단계 처리 시간 (밀리초)")
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False, comment="이벤트 발생 일시 (UTC)")


class EvidenceReference(Base):
    __tablename__ = "evidence_reference"
    __table_args__ = {"comment": "Tool 호출로 획득한 실제 데이터 근거. AI 응답의 출처를 추적하고 신뢰도를 정량화한다. confidence_score = 0.5×data_quality + 0.4×intent_relevance + 0.1×latency_bonus 로 산출한다."}

    id                     = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id             = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    concept_id             = Column(String(100), nullable=True, comment="이 근거가 해당하는 업무 개념 ID")
    source_type            = Column(String(50), nullable=True, comment="근거 출처 유형 (예: api)")
    source_id              = Column(String(100), nullable=True, comment="근거를 제공한 API ID (예: MOCK_RATE_LOOKUP)")
    content                = Column(JSON, nullable=True, comment="API 응답 원본 데이터 JSON")
    confidence_score       = Column(Float, default=1.0, nullable=True, comment="최종 종합 신뢰도 (0.0~1.0)")
    data_quality_score     = Column(Float, default=None, nullable=True, comment="데이터 완성도 점수 — 필수 필드 존재 여부·항목 수 기반 (가중치 50%)")
    intent_relevance_score = Column(Float, default=None, nullable=True, comment="사용자 의도와의 관련도 점수 (가중치 40%)")
    response_latency_ms    = Column(Integer, default=None, nullable=True, comment="API 응답 시간 (ms) — 2초 이내이면 latency_bonus 1.0 적용")
    item_count             = Column(Integer, default=None, nullable=True, comment="API가 반환한 데이터 레코드 수 (단건=1, 목록=N)")
    quality_flags          = Column(JSON, default=None, nullable=True, comment="API별 세부 품질 체크 결과 (예: {\"has_annual_rate\": true})")
    related_evidence_ids   = Column(JSON, default=None, nullable=True, comment="온톨로지 관계로 연결된 다른 EvidenceReference.id 목록 — link_related_evidence()가 채운다")
    agent_id               = Column(String(100), nullable=True, comment="이 근거를 생성한 Sub-Agent ID")
    created_at             = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class DecisionTrace(Base):
    __tablename__ = "ai_decision_trace"
    __table_args__ = {"comment": "요청 1건의 최상위 Decision Trace 요약. 운영자 화면(Summary / Evidence View)이 공통으로 참조하는 엔트리다. request_id는 UNIQUE이며 메타데이터·memory·intent·latency를 JSONB로 통합 저장한다."}

    id               = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id       = Column(String(100), nullable=False, unique=True, index=True, comment="요청 고유 ID (UNIQUE)")
    session_id       = Column(String(100), nullable=True, index=True, comment="Redis Short Memory 세션 ID")
    owner_name       = Column(String(100), nullable=True, index=True, comment="요청한 사용자 이름")
    owner_role       = Column(String(32), nullable=True, index=True, comment="요청한 사용자 역할: ADMIN / ANALYST / READONLY")
    user_query       = Column(Text, nullable=False, comment="사용자 원본 질문")
    normalized_query = Column(Text, nullable=True, comment="정규화·전처리된 질문")
    request_meta     = Column(JSONB, nullable=True, default=dict, comment="요청 메타데이터 JSONB (헤더, 클라이언트 정보 등)")
    memory_summary   = Column(JSONB, nullable=True, default=dict, comment="Short/Long Memory 로드 요약 JSONB")
    intent_analysis  = Column(JSONB, nullable=True, default=dict, comment="의도 분석 결과 전체 JSONB")
    latency          = Column(JSONB, nullable=True, default=dict, comment="단계별 처리 시간 집계 JSONB")
    status           = Column(String(32), nullable=False, default="completed", comment="처리 상태: completed / error / timeout")
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class ConceptDetectionTrace(Base):
    __tablename__ = "ai_concept_detection"
    __table_args__ = {"comment": "Concept 탐지 결과를 concept 단위로 저장하는 테이블. 직접 탐지(direct)와 온톨로지 확장(expanded)을 구분하고, 신뢰도·소스·이유를 각 행에 기록한다."}

    id              = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id      = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    concept_id      = Column(String(100), nullable=False, index=True, comment="탐지된 concept ID")
    detection_stage = Column(String(32), nullable=False, comment="탐지 단계: direct / expanded")
    confidence      = Column(Float, nullable=True, comment="탐지 신뢰도 (0.0~1.0)")
    source_type     = Column(String(32), nullable=True, comment="탐지 소스 유형: alias / keyword / relation")
    source_terms    = Column(JSONB, nullable=True, default=list, comment="매칭된 alias·키워드 목록 JSONB")
    relation_path   = Column(JSONB, nullable=True, default=list, comment="온톨로지 확장 경로 JSONB (expanded일 때)")
    reason          = Column(Text, nullable=True, comment="탐지 근거 설명")
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class AgentSelectionTrace(Base):
    __tablename__ = "ai_agent_selection"
    __table_args__ = {"comment": "Agent 후보별 선택·미선택 사유 기록. selected=False 행도 저장해 왜 제외됐는지 사후에 추적할 수 있다. Decision Rule 평가 결과(role·execution_mode·tools_assigned·decision_rule_ids)도 포함한다."}

    id                = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id        = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    agent_id          = Column(String(100), nullable=False, index=True, comment="평가 대상 Agent ID")
    selected          = Column(Boolean, nullable=False, default=False, comment="최종 선택 여부")
    score             = Column(Float, nullable=True, comment="선택 점수")
    matched_concepts  = Column(JSONB, nullable=True, default=list, comment="이 Agent와 매칭된 concept ID 목록 JSONB")
    reason            = Column(Text, nullable=False, comment="선택 근거")
    rejection_reason  = Column(Text, nullable=True, comment="미선택 이유 (selected=False일 때)")
    role              = Column(String(100), nullable=True, comment="Decision Rule 평가 결과 — Agent 역할")
    execution_mode    = Column(String(50), nullable=True, comment="실행 모드 (예: parallel / sequential)")
    tools_assigned    = Column(JSONB, nullable=True, default=list, comment="이 Agent에 배정된 Tool 목록 JSONB")
    decision_rule_ids = Column(JSONB, nullable=True, default=list, comment="적용된 Decision Rule ID 목록 JSONB")
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class ToolExecutionTrace(Base):
    __tablename__ = "ai_tool_execution"
    __table_args__ = {"comment": "Tool 실행 1건 로그. 운영자 화면에서 input/output 요약·상태·latency·연결 evidence를 표시한다. request 단위 Tool 실행 이력을 추적하는 용도."}

    id             = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id     = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    agent_id       = Column(String(100), nullable=False, index=True, comment="Tool을 호출한 Agent ID")
    tool_code      = Column(String(100), nullable=False, index=True, comment="실행된 Tool 코드 (api_catalog.api_id)")
    concept_ids    = Column(JSONB, nullable=True, default=list, comment="이 Tool 실행과 연관된 concept ID 목록 JSONB")
    input_summary  = Column(Text, nullable=True, comment="Tool 입력 요약")
    output_summary = Column(Text, nullable=True, comment="Tool 출력 요약")
    status         = Column(String(32), nullable=False, comment="실행 결과: success / error / timeout")
    latency_ms     = Column(Integer, nullable=True, comment="Tool 응답 시간 (ms)")
    error_summary  = Column(Text, nullable=True, comment="에러 발생 시 오류 메시지 요약")
    evidence_ids   = Column(JSONB, nullable=True, default=list, comment="이 실행으로 생성된 EvidenceReference.id 목록 JSONB")
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class RerankingTrace(Base):
    __tablename__ = "ai_reranking_trace"
    __table_args__ = {"comment": "Re-ranking 결과 1건. request_id는 UNIQUE. criteria_weights와 후보별 score breakdown을 JSONB로 저장해 어떤 근거가 최종 답변에 선택됐는지 추적한다."}

    id                   = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id           = Column(String(100), nullable=False, unique=True, index=True, comment="요청 고유 ID (UNIQUE)")
    criteria_weights     = Column(JSONB, nullable=True, default=dict, comment="재정렬 기준 가중치 JSONB")
    candidates           = Column(JSONB, nullable=True, default=list, comment="재정렬 후보 및 점수 상세 JSONB")
    selected_evidence_ids= Column(JSONB, nullable=True, default=list, comment="최종 선택된 EvidenceReference.id 목록 JSONB")
    reason               = Column(Text, nullable=True, comment="재정렬 결과 설명")
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class FinalAnswerTrace(Base):
    __tablename__ = "ai_final_answer_trace"
    __table_args__ = {"comment": "최종 답변과 grounding 메타데이터 1건. request_id는 UNIQUE. 어떤 Evidence를 근거로 답변이 생성됐는지 추적하는 용도."}

    id               = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id       = Column(String(100), nullable=False, unique=True, index=True, comment="요청 고유 ID (UNIQUE)")
    answer           = Column(Text, nullable=False, comment="최종 LLM 생성 답변 전문")
    answer_summary   = Column(Text, nullable=True, comment="답변 요약 (UI 미리보기용)")
    used_evidence_ids= Column(JSONB, nullable=True, default=list, comment="답변 생성에 사용된 EvidenceReference.id 목록 JSONB")
    grounding_summary= Column(Text, nullable=True, comment="근거(grounding) 설명 요약")
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class LeaderDecisionNode(Base):
    __tablename__ = "leader_decision_node"
    __table_args__ = {"comment": "Decision Graph의 노드 1개. request_id 기준으로 Leader Agent 판단 단계(의도 분석·Concept 탐지·Agent 선택·Tool 호출·최종 답변)를 각 1행으로 기록한다. data JSONB에 단계별 상세 정보를 저장해 그래프 API에서 조인 없이 응답 가능."}

    id             = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id     = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    node_id        = Column(String(160), nullable=False, unique=True, comment="노드 고유 ID (예: req-xxx::intent)")
    node_type      = Column(String(32), nullable=False, comment="노드 유형: intent / concept / agent / tool / answer 등")
    node_label     = Column(String(128), nullable=True, comment="그래프 UI 표시용 라벨")
    status         = Column(String(16), nullable=False, default="SUCCESS", comment="노드 처리 결과: SUCCESS / ERROR / SKIP")
    sequence_order = Column(Integer, nullable=False, default=0, comment="처리 순서 (낮을수록 먼저 실행)")
    position_x     = Column(Float, nullable=True, default=0.0, comment="그래프 UI 노드 X 좌표")
    position_y     = Column(Float, nullable=True, default=0.0, comment="그래프 UI 노드 Y 좌표")
    data           = Column(JSONB, nullable=False, default=dict, comment="단계별 상세 정보 JSONB")
    style          = Column(JSONB, nullable=True, default=dict, comment="그래프 UI 스타일 JSONB")
    duration_ms    = Column(Integer, nullable=True, comment="이 노드 처리 시간 (ms)")
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow, comment="레코드 생성 일시 (UTC)")


class LeaderDecisionEdge(Base):
    __tablename__ = "leader_decision_edge"
    __table_args__ = {"comment": "Decision Graph의 엣지 1개 (source_node → target_node). edge_type으로 관계 의미를 구분한다: HAS_INTENT / INFLUENCES / DETECTS / HANDLED_BY / SELECTS / CALLS / RETURNS / SCORED_BY / SUPPORTS / PRODUCES"}

    id             = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id     = Column(String(100), nullable=False, index=True, comment="요청 고유 ID")
    edge_id        = Column(String(160), nullable=False, unique=True, comment="엣지 고유 ID")
    edge_type      = Column(String(32), nullable=False, comment="엣지 유형: HAS_INTENT / DETECTS / SELECTS / CALLS / RETURNS 등")
    edge_label     = Column(String(64), nullable=True, comment="그래프 UI 표시용 라벨")
    source_node_id = Column(String(160), nullable=False, index=True, comment="출발 노드 ID (FK 논리적 참조 → leader_decision_node.node_id)")
    target_node_id = Column(String(160), nullable=False, index=True, comment="도착 노드 ID (FK 논리적 참조 → leader_decision_node.node_id)")
    data           = Column(JSONB, nullable=True, default=dict, comment="엣지 부가 정보 JSONB")
    style          = Column(JSONB, nullable=True, default=dict, comment="그래프 UI 스타일 JSONB")
    weight         = Column(Float, nullable=True, default=1.0, comment="엣지 가중치 (시각화·필터링용)")
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow, comment="레코드 생성 일시 (UTC)")


class LeaderDecisionReview(Base):
    __tablename__ = "leader_decision_review"
    __table_args__ = {"comment": "Reviewer(사람)가 Decision Graph 1건을 검토한 결과. 의도 정확성·Concept 완전성·Agent 선택·Evidence 충분성·답변 적절성을 Boolean으로 평가한다. request_id는 UNIQUE — 1건당 최신 리뷰 1개만 유지."}

    id                  = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id          = Column(String(100), nullable=False, unique=True, index=True, comment="요청 고유 ID (UNIQUE)")
    reviewer_id         = Column(String(64), nullable=True, comment="검토자 식별자")
    status              = Column(String(16), nullable=True, default="PENDING", comment="검토 상태: PENDING / IN_REVIEW / DONE")
    overall_result      = Column(String(32), nullable=True, comment="종합 결과: PASS / FAIL / NEEDS_REVIEW")
    intent_correct      = Column(Boolean, nullable=True, comment="의도 분류 정확성 평가")
    concept_complete    = Column(Boolean, nullable=True, comment="Concept 탐지 완전성 평가")
    agent_correct       = Column(Boolean, nullable=True, comment="Agent 선택 정확성 평가")
    evidence_sufficient = Column(Boolean, nullable=True, comment="Evidence 충분성 평가")
    answer_appropriate  = Column(Boolean, nullable=True, comment="최종 답변 적절성 평가")
    missing_concepts    = Column(JSON, nullable=True, comment="누락된 concept 목록")
    wrong_agents        = Column(JSON, nullable=True, comment="잘못 선택된 Agent 목록")
    comment             = Column(Text, nullable=True, comment="검토자 코멘트")
    review_score        = Column(Float, nullable=True, comment="종합 점수 (0.0~1.0)")
    reviewed_at         = Column(DateTime, nullable=True, comment="검토 완료 일시 (UTC)")
    created_at          = Column(DateTime, nullable=False, default=datetime.utcnow, comment="레코드 생성 일시 (UTC)")
