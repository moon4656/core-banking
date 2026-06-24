"""test_monitor_model.py — mon_* 테이블 생성 및 CRUD 단위 테스트

전제 조건:
  - alembic upgrade head 완료 (0014_add_monitor_tables)
  - docker compose exec backend pytest tests/test_monitor_model.py -v
"""
import pytest
from sqlalchemy import inspect, text

from app.models.monitor_model import (
    MonAgentTrace,
    MonIntentAnalysis,
    MonConceptDetection,
    MonRoutingDecision,
    MonToolExecution,
    MonAnswerSentence,
    MonGateCheck,
)

REQUEST_ID = "TEST-MON-0001"

# ── 픽스처 ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def cleanup(db):
    """각 테스트 전후 테스트 데이터를 삭제한다."""
    _delete_test_data(db)
    yield
    _delete_test_data(db)


def _delete_test_data(db):
    for model in (
        MonGateCheck, MonAnswerSentence, MonToolExecution,
        MonRoutingDecision, MonConceptDetection, MonIntentAnalysis,
        MonAgentTrace,
    ):
        db.query(model).filter(model.request_id == REQUEST_ID).delete()
    db.commit()


# ── 테이블 존재 확인 ──────────────────────────────────────────────────────

EXPECTED_TABLES = [
    "mon_agent_trace",
    "mon_intent_analysis",
    "mon_concept_detection",
    "mon_routing_decision",
    "mon_tool_execution",
    "mon_answer_sentence",
    "mon_gate_check",
]


def test_all_mon_tables_exist(db):
    """7개 mon_* 테이블이 모두 생성되어 있어야 한다."""
    inspector = inspect(db.bind)
    existing = inspector.get_table_names()
    for table in EXPECTED_TABLES:
        assert table in existing, f"테이블 누락: {table}"


# ── 컬럼 구조 검증 ─────────────────────────────────────────────────────────

def test_mon_agent_trace_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_agent_trace")}
    required = {"id", "request_id", "user_id", "session_id",
                "original_query", "normalized_query", "status",
                "total_latency_ms", "created_at"}
    assert required <= cols


def test_mon_intent_analysis_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_intent_analysis")}
    required = {"id", "request_id", "primary_intent", "secondary_intents",
                "query_type", "needs_tool_execution", "needs_memory",
                "confidence", "reason", "created_at"}
    assert required <= cols


def test_mon_concept_detection_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_concept_detection")}
    required = {"id", "request_id", "source_text", "concept_id",
                "concept_label", "concept_type", "confidence",
                "expanded_terms", "status", "created_at"}
    assert required <= cols


def test_mon_routing_decision_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_routing_decision")}
    required = {"id", "request_id", "agent_name", "selected",
                "related_concepts", "reason", "routing_confidence",
                "execution_order", "status", "created_at"}
    assert required <= cols


def test_mon_tool_execution_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_tool_execution")}
    required = {"id", "request_id", "agent_name", "tool_name",
                "tool_input", "output_summary", "status",
                "latency_ms", "retry_count", "error_message", "created_at"}
    assert required <= cols


def test_mon_answer_sentence_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_answer_sentence")}
    required = {"id", "request_id", "answer_sentence", "source_agent",
                "source_tool", "evidence_summary", "grounded",
                "warning_message", "created_at"}
    assert required <= cols


def test_mon_gate_check_columns(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("mon_gate_check")}
    required = {"id", "request_id", "gate_name", "gate_type",
                "condition", "result", "severity", "message", "created_at"}
    assert required <= cols


# ── CRUD 통합 검증 ─────────────────────────────────────────────────────────

def test_insert_and_query_full_trace(db):
    """7개 테이블에 1건씩 INSERT 후 request_id로 조회 가능해야 한다."""
    # 1. 헤더
    trace = MonAgentTrace(
        request_id=REQUEST_ID,
        user_id="user_test",
        session_id="session_test",
        original_query="개인신용대출 금리 알려줘",
        normalized_query="개인신용대출의 금리 정보를 조회한다",
        status="completed",
        total_latency_ms=1200,
    )
    db.add(trace)

    # 2. 의미분석
    db.add(MonIntentAnalysis(
        request_id=REQUEST_ID,
        primary_intent="loan_information_lookup",
        secondary_intents=["interest_rate_lookup"],
        query_type="single_topic",
        needs_tool_execution=True,
        needs_memory=False,
        confidence=0.92,
        reason="개인신용대출과 금리 키워드가 탐지됨",
    ))

    # 3. Concept 탐지 — 정상
    db.add(MonConceptDetection(
        request_id=REQUEST_ID,
        source_text="개인신용대출",
        concept_id="CONCEPT_PERSONAL_CREDIT_LOAN",
        concept_label="개인신용대출",
        concept_type="loan_product",
        confidence=0.96,
        expanded_terms=["신용대출", "개인대출"],
        status="normal",
    ))

    # 4. Concept 탐지 — 낮은 confidence (Gate 1 대상)
    db.add(MonConceptDetection(
        request_id=REQUEST_ID,
        source_text="금리",
        concept_id="CONCEPT_INTEREST_RATE",
        concept_label="금리",
        concept_type="rate",
        confidence=0.62,
        expanded_terms=["이자율"],
        status="low_confidence",
    ))

    # 5. Agent 라우팅 — 선택
    db.add(MonRoutingDecision(
        request_id=REQUEST_ID,
        agent_name="RATE_AGENT",
        selected=True,
        related_concepts=["CONCEPT_INTEREST_RATE"],
        reason="금리 정보 조회 필요",
        routing_confidence=0.95,
        execution_order=1,
        status="selected",
    ))

    # 6. Agent 라우팅 — 제외
    db.add(MonRoutingDecision(
        request_id=REQUEST_ID,
        agent_name="CUSTOMER_AGENT",
        selected=False,
        related_concepts=[],
        reason="고객 정보 조회 필요 없음",
        routing_confidence=0.88,
        execution_order=None,
        status="excluded",
    ))

    # 7. Tool 실행
    db.add(MonToolExecution(
        request_id=REQUEST_ID,
        agent_name="RATE_AGENT",
        tool_name="MOCK_RATE_LOOKUP",
        tool_input={"product_type": "personal_credit_loan"},
        output_summary="개인신용대출 금리: 최저 연 4.2%, 최고 연 9.8%",
        status="success",
        latency_ms=320,
        retry_count=0,
    ))

    # 8. 답변 문장 — 근거 있음
    db.add(MonAnswerSentence(
        request_id=REQUEST_ID,
        answer_sentence="개인신용대출 금리는 최저 연 4.2%, 최고 연 9.8%입니다.",
        source_agent="RATE_AGENT",
        source_tool="MOCK_RATE_LOOKUP",
        evidence_summary="금리 조회 결과: 최저 연 4.2%, 최고 연 9.8%",
        grounded=True,
    ))

    # 9. 답변 문장 — 근거 없음 (Gate 3 대상)
    db.add(MonAnswerSentence(
        request_id=REQUEST_ID,
        answer_sentence="일반적으로 연소득의 3배까지 대출이 가능합니다.",
        source_agent=None,
        source_tool=None,
        evidence_summary=None,
        grounded=False,
        warning_message="Hallucination 가능성. 검토 필요.",
    ))

    # 10. Gate 체크
    for gate_name, gate_type, result, severity, message in [
        ("concept_confidence", "WARNING", "WARNING", "warning",
         "CONCEPT_INTEREST_RATE confidence 0.62 < 0.7"),
        ("agent_routing",      "BLOCK",   "PASS",    "critical", None),
        ("answer_grounding",   "WARNING", "WARNING", "warning",
         "근거 없는 문장 1개 감지. Hallucination 가능성."),
    ]:
        db.add(MonGateCheck(
            request_id=REQUEST_ID,
            gate_name=gate_name,
            gate_type=gate_type,
            result=result,
            severity=severity,
            message=message,
        ))

    db.commit()

    # ── 조회 검증 ──────────────────────────────────────────────────────────
    loaded = db.query(MonAgentTrace).filter_by(request_id=REQUEST_ID).one()
    assert loaded.status == "completed"
    assert loaded.total_latency_ms == 1200

    concepts = db.query(MonConceptDetection).filter_by(request_id=REQUEST_ID).all()
    assert len(concepts) == 2
    low = [c for c in concepts if c.status == "low_confidence"]
    assert len(low) == 1
    assert low[0].confidence == pytest.approx(0.62)

    selected_agents = (
        db.query(MonRoutingDecision)
        .filter_by(request_id=REQUEST_ID, selected=True)
        .all()
    )
    assert len(selected_agents) == 1
    assert selected_agents[0].agent_name == "RATE_AGENT"
    assert selected_agents[0].execution_order == 1

    tool = db.query(MonToolExecution).filter_by(request_id=REQUEST_ID).one()
    assert tool.tool_input == {"product_type": "personal_credit_loan"}
    assert tool.retry_count == 0

    sentences = db.query(MonAnswerSentence).filter_by(request_id=REQUEST_ID).all()
    assert len(sentences) == 2
    ungrounded = [s for s in sentences if not s.grounded]
    assert len(ungrounded) == 1

    gates = db.query(MonGateCheck).filter_by(request_id=REQUEST_ID).all()
    assert len(gates) == 3
    blocked_gates = [g for g in gates if g.result == "BLOCKED"]
    assert len(blocked_gates) == 0   # agent_routing은 PASS


# ── Gate 1: confidence < 0.7 감지 검증 ─────────────────────────────────────

def test_gate1_low_confidence_detection(db):
    """confidence < 0.7인 Concept가 저장된 후 Gate 1 WARNING 레코드와 함께 조회된다."""
    db.add(MonAgentTrace(
        request_id=REQUEST_ID,
        original_query="테스트 질의",
        status="warning",
    ))
    db.add(MonConceptDetection(
        request_id=REQUEST_ID,
        concept_id="CONCEPT_REQUIRED_DOCUMENT",
        confidence=0.55,
        status="low_confidence",
    ))
    db.add(MonGateCheck(
        request_id=REQUEST_ID,
        gate_name="concept_confidence",
        gate_type="WARNING",
        condition="confidence < 0.7",
        result="WARNING",
        severity="warning",
        message="CONCEPT_REQUIRED_DOCUMENT confidence 0.55 < 0.7",
    ))
    db.commit()

    gate = (
        db.query(MonGateCheck)
        .filter_by(request_id=REQUEST_ID, gate_name="concept_confidence")
        .one()
    )
    assert gate.result == "WARNING"
    assert "0.55" in gate.message


# ── Gate 2: Agent Routing 비어 있는 경우 ──────────────────────────────────

def test_gate2_no_selected_agents(db):
    """선택된 Agent가 0개일 때 Gate 2 BLOCKED 레코드가 저장된다."""
    db.add(MonAgentTrace(
        request_id=REQUEST_ID,
        original_query="인식 불가 질의",
        status="blocked",
    ))
    db.add(MonRoutingDecision(
        request_id=REQUEST_ID,
        agent_name="RATE_AGENT",
        selected=False,
        status="excluded",
        reason="매핑된 Concept 없음",
    ))
    db.add(MonGateCheck(
        request_id=REQUEST_ID,
        gate_name="agent_routing",
        gate_type="BLOCK",
        condition="selected_agents.length == 0",
        result="BLOCKED",
        severity="critical",
        message="선택된 Agent가 없습니다. Sub-Agent 실행 중단.",
    ))
    db.commit()

    gate = (
        db.query(MonGateCheck)
        .filter_by(request_id=REQUEST_ID, gate_name="agent_routing")
        .one()
    )
    assert gate.result == "BLOCKED"

    selected = (
        db.query(MonRoutingDecision)
        .filter_by(request_id=REQUEST_ID, selected=True)
        .count()
    )
    assert selected == 0


# ── Gate 3: 근거 없는 문장 감지 ───────────────────────────────────────────

def test_gate3_ungrounded_sentence(db):
    """grounded=False 문장 존재 시 Gate 3 WARNING 레코드가 저장된다."""
    db.add(MonAgentTrace(
        request_id=REQUEST_ID,
        original_query="테스트 질의",
        status="warning",
    ))
    db.add(MonAnswerSentence(
        request_id=REQUEST_ID,
        answer_sentence="대출 한도는 최대 1억 원입니다.",
        grounded=False,
        warning_message="Tool 결과에 없는 내용. Hallucination 가능성.",
    ))
    db.add(MonGateCheck(
        request_id=REQUEST_ID,
        gate_name="answer_grounding",
        gate_type="WARNING",
        condition="grounded == false",
        result="WARNING",
        severity="warning",
        message="근거 없는 문장 감지. 검토 필요.",
    ))
    db.commit()

    gate = (
        db.query(MonGateCheck)
        .filter_by(request_id=REQUEST_ID, gate_name="answer_grounding")
        .one()
    )
    assert gate.result == "WARNING"

    ungrounded_count = (
        db.query(MonAnswerSentence)
        .filter_by(request_id=REQUEST_ID, grounded=False)
        .count()
    )
    assert ungrounded_count == 1
