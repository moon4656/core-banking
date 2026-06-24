"""test_monitor_pipeline.py — Leader Agent 파이프라인 → mon_* 테이블 통합 테스트

전제 조건:
  - alembic upgrade head (0014_add_monitor_tables 포함)
  - python -m app.seed.run_seed 완료
  - docker compose exec backend pytest tests/test_monitor_pipeline.py -v
"""
import pytest

from app.models.monitor_model import (
    MonAgentTrace,
    MonAnswerSentence,
    MonConceptDetection,
    MonGateCheck,
    MonIntentAnalysis,
    MonRoutingDecision,
    MonToolExecution,
)
from app.services.monitoring_service import (
    MonitoringService,
    _check_grounding,
    _split_sentences,
    _summarize_tool_output,
)

# ── 공통 fixtures ──────────────────────────────────────────────────────────

REQUEST_ID = "TEST-PIPELINE-0001"

CONCEPT_ROWS_NORMAL = [
    {
        "concept_id": "CONCEPT_PERSONAL_CREDIT_LOAN",
        "detection_stage": "direct",
        "confidence": 0.96,
        "source_type": "query",
        "source_terms": ["개인신용대출"],
        "reason": "alias 매칭",
    },
    {
        "concept_id": "CONCEPT_INTEREST_RATE",
        "detection_stage": "direct",
        "confidence": 0.93,
        "source_type": "query",
        "source_terms": ["금리"],
        "reason": "alias 매칭",
    },
]

CONCEPT_ROWS_LOW_CONF = CONCEPT_ROWS_NORMAL + [
    {
        "concept_id": "CONCEPT_REQUIRED_DOCUMENT",
        "detection_stage": "direct",
        "confidence": 0.62,
        "source_type": "query",
        "source_terms": ["필요 서류"],
        "reason": "alias 매칭 (낮은 신뢰도)",
    },
]

AGENT_SELECTION_ROWS = [
    {
        "agent_id": "RATE_AGENT",
        "selected": True,
        "score": 1.0,
        "matched_concepts": ["CONCEPT_INTEREST_RATE"],
        "reason": "금리 정보 조회 필요",
        "rejection_reason": None,
    },
    {
        "agent_id": "POLICY_AGENT",
        "selected": True,
        "score": 1.0,
        "matched_concepts": ["CONCEPT_REQUIRED_DOCUMENT"],
        "reason": "필요서류 정보 조회 필요",
        "rejection_reason": None,
    },
    {
        "agent_id": "PRODUCT_AGENT",
        "selected": False,
        "score": 0.0,
        "matched_concepts": [],
        "reason": "No matched concepts",
        "rejection_reason": "concept-agent 매핑 없음",
    },
]

INTENT_DATA = {
    "intent": "INQUIRY",
    "keywords": ["개인신용대출", "금리"],
    "urgency": "low",
}


@pytest.fixture(autouse=True)
def cleanup(db):
    _delete(db)
    yield
    _delete(db)


def _delete(db):
    for model in (
        MonGateCheck, MonAnswerSentence, MonToolExecution,
        MonRoutingDecision, MonConceptDetection, MonIntentAnalysis,
        MonAgentTrace,
    ):
        db.query(model).filter(model.request_id == REQUEST_ID).delete()
    db.commit()


# ══════════════════════════════════════════════════════════════════════════
# 유틸리티 함수 단위 테스트
# ══════════════════════════════════════════════════════════════════════════

class TestSplitSentences:
    def test_bullet_lines(self):
        text = "■ 금리 안내\n  · 직장인 신용대출: 4.2% ~ 9.8%\n  · 프리랜서 대출: 5.8% ~ 13.5%"
        sentences = _split_sentences(text)
        assert len(sentences) >= 3
        assert any("4.2%" in s for s in sentences)

    def test_period_split(self):
        text = "금리는 최저 4.2%입니다. 우대금리는 최대 0.5%p입니다."
        sentences = _split_sentences(text)
        assert len(sentences) >= 1

    def test_short_fragments_excluded(self):
        sentences = _split_sentences("안녕")
        assert len(sentences) == 0


class TestCheckGrounding:
    def setup_method(self):
        self.tool_output_map = {
            "MOCK_RATE_LOOKUP": {
                "agent":     "RATE_AGENT",
                "data_text": '{"rates":[{"min_final_rate":"4.2","max_final_rate":"9.8"}]}',
                "summary":   "금리: 4.2% ~ 9.8%",
            },
        }

    def test_grounded_sentence_with_matching_rate(self):
        grounded, agent, tool, summary = _check_grounding(
            "· 직장인 신용대출: 4.2% ~ 9.8%",
            self.tool_output_map,
        )
        assert grounded is True
        assert tool == "MOCK_RATE_LOOKUP"
        assert agent == "RATE_AGENT"

    def test_ungrounded_sentence_unknown_rate(self):
        grounded, agent, tool, summary = _check_grounding(
            "대출 한도는 최대 1억 원입니다.",
            self.tool_output_map,
        )
        assert grounded is False
        assert agent is None

    def test_no_numbers_grounded_by_default(self):
        grounded, agent, tool, summary = _check_grounding(
            "영업점을 방문하시거나 앱을 통해 신청하세요.",
            self.tool_output_map,
        )
        assert grounded is True


class TestSummarizeToolOutput:
    def test_rate_lookup(self):
        data = {"rates": [{"product_name": "직장인 신용대출",
                           "min_final_rate": "4.2",
                           "max_final_rate": "9.8"}]}
        summary = _summarize_tool_output("MOCK_RATE_LOOKUP", data)
        assert "4.2%" in summary or "9.8%" in summary

    def test_empty_data(self):
        assert _summarize_tool_output("MOCK_RATE_LOOKUP", None) == "데이터 없음"
        assert _summarize_tool_output("MOCK_RATE_LOOKUP", {}) == "데이터 없음"


# ══════════════════════════════════════════════════════════════════════════
# MonitoringService 단위 테스트
# ══════════════════════════════════════════════════════════════════════════

class TestCreateTrace:
    def test_creates_processing_record(self, db):
        MonitoringService.create_trace(
            db, REQUEST_ID, "user_test", "sess_001", "금리 알려줘"
        )
        trace = db.query(MonAgentTrace).filter_by(request_id=REQUEST_ID).one()
        assert trace.status == "processing"
        assert trace.user_id == "user_test"
        assert trace.original_query == "금리 알려줘"


class TestConceptDetectionAndGate1:
    def test_all_normal_confidence_gate1_pass(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        triggered = MonitoringService.save_concept_detections_and_gate1(
            db, REQUEST_ID, CONCEPT_ROWS_NORMAL
        )
        assert triggered is False

        rows = db.query(MonConceptDetection).filter_by(request_id=REQUEST_ID).all()
        assert len(rows) == 2
        assert all(r.status == "normal" for r in rows)

        gate = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="concept_confidence"
        ).one()
        assert gate.result == "PASS"

    def test_low_confidence_triggers_gate1_warning(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        triggered = MonitoringService.save_concept_detections_and_gate1(
            db, REQUEST_ID, CONCEPT_ROWS_LOW_CONF
        )
        assert triggered is True

        low_rows = db.query(MonConceptDetection).filter_by(
            request_id=REQUEST_ID, status="low_confidence"
        ).all()
        assert len(low_rows) == 1
        assert low_rows[0].concept_id == "CONCEPT_REQUIRED_DOCUMENT"

        gate = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="concept_confidence"
        ).one()
        assert gate.result == "WARNING"
        assert "0.62" in gate.message


class TestRoutingDecisionAndGate2:
    def setup_trace(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")

    def test_agents_selected_gate2_pass(self, db):
        self.setup_trace(db)
        routed = ["RATE_AGENT", "POLICY_AGENT"]
        blocked = MonitoringService.save_routing_decisions_and_gate2(
            db, REQUEST_ID, AGENT_SELECTION_ROWS, routed
        )
        assert blocked is False

        selected = db.query(MonRoutingDecision).filter_by(
            request_id=REQUEST_ID, selected=True
        ).all()
        assert len(selected) == 2

        # 실행 순서 확인
        rate_row = next(r for r in selected if r.agent_name == "RATE_AGENT")
        assert rate_row.execution_order == 1

        gate = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="agent_routing"
        ).one()
        assert gate.result == "PASS"

    def test_no_agents_triggers_gate2_blocked(self, db):
        self.setup_trace(db)
        all_excluded = [
            {**row, "selected": False, "matched_concepts": [],
             "reason": None, "rejection_reason": "매핑 없음"}
            for row in AGENT_SELECTION_ROWS
        ]
        blocked = MonitoringService.save_routing_decisions_and_gate2(
            db, REQUEST_ID, all_excluded, []
        )
        assert blocked is True

        gate = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="agent_routing"
        ).one()
        assert gate.result == "BLOCKED"
        assert gate.severity == "critical"


class TestToolExecution:
    def test_save_success(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        MonitoringService.save_tool_execution(
            db, REQUEST_ID,
            agent_name="RATE_AGENT",
            tool_name="MOCK_RATE_LOOKUP",
            tool_input={"concept_ids": ["CONCEPT_INTEREST_RATE"]},
            output_summary="금리: 4.2% ~ 9.8%",
            status="success",
            latency_ms=320,
            retry_count=0,
        )
        tool = db.query(MonToolExecution).filter_by(request_id=REQUEST_ID).one()
        assert tool.status == "success"
        assert tool.tool_input == {"concept_ids": ["CONCEPT_INTEREST_RATE"]}
        assert tool.latency_ms == 320

    def test_save_failure_with_error(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        MonitoringService.save_tool_execution(
            db, REQUEST_ID,
            agent_name="RATE_AGENT",
            tool_name="MOCK_RATE_LOOKUP",
            tool_input={},
            output_summary=None,
            status="failed",
            latency_ms=5000,
            retry_count=2,
            error_message="Connection timeout",
        )
        tool = db.query(MonToolExecution).filter_by(request_id=REQUEST_ID).one()
        assert tool.status == "failed"
        assert tool.retry_count == 2
        assert "timeout" in tool.error_message


class TestIntentAnalysis:
    def test_multi_topic_query(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        MonitoringService.save_intent_analysis(
            db, REQUEST_ID, INTENT_DATA,
            detected_concepts=["CONCEPT_INTEREST_RATE", "CONCEPT_REQUIRED_DOCUMENT"],
            all_concepts=["CONCEPT_INTEREST_RATE", "CONCEPT_REQUIRED_DOCUMENT"],
            routed_agents=["RATE_AGENT", "POLICY_AGENT"],
        )
        record = db.query(MonIntentAnalysis).filter_by(request_id=REQUEST_ID).one()
        assert record.primary_intent == "INQUIRY"
        assert record.query_type == "multi_topic"
        assert record.needs_tool_execution is True
        assert "interest_rate_lookup" in record.secondary_intents

    def test_single_topic_no_tools(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        MonitoringService.save_intent_analysis(
            db, REQUEST_ID, INTENT_DATA,
            detected_concepts=["CONCEPT_INTEREST_RATE"],
            all_concepts=["CONCEPT_INTEREST_RATE"],
            routed_agents=[],
        )
        record = db.query(MonIntentAnalysis).filter_by(request_id=REQUEST_ID).one()
        assert record.query_type == "single_topic"
        assert record.needs_tool_execution is False


class TestAnswerSentencesAndGate3:
    """최종 답변 근거 추적 + Gate 3 체크"""

    class _MockStepResult:
        def __init__(self, api_id, status, data):
            self.api_id = api_id
            self.status = status
            self.data = data

    def _make_raw_results(self, has_rate=True):
        results = []
        if has_rate:
            results.append(self._MockStepResult(
                "MOCK_RATE_LOOKUP", "success",
                {"rates": [{"product_name": "직장인 신용대출",
                            "min_final_rate": "4.2",
                            "max_final_rate": "9.8"}]}
            ))
        return results

    def test_grounded_answer_gate3_pass(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        answer = "■ 금리 안내\n  · 직장인 신용대출: 4.2% ~ 9.8%"
        triggered = MonitoringService.save_answer_sentences_and_gate3(
            db, REQUEST_ID, answer, self._make_raw_results(),
            tool_agent_map={"MOCK_RATE_LOOKUP": "RATE_AGENT"},
        )
        assert triggered is False

        gate = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="answer_grounding"
        ).one()
        assert gate.result == "PASS"

        sentences = db.query(MonAnswerSentence).filter_by(request_id=REQUEST_ID).all()
        assert len(sentences) >= 1

    def test_hallucinated_sentence_triggers_gate3(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        answer = (
            "■ 금리 안내\n"
            "  · 직장인 신용대출: 4.2% ~ 9.8%\n"
            "  · 한도는 최대 5억 원까지 가능합니다."   # 5억 원은 tool output에 없음
        )
        triggered = MonitoringService.save_answer_sentences_and_gate3(
            db, REQUEST_ID, answer, self._make_raw_results(),
            tool_agent_map={"MOCK_RATE_LOOKUP": "RATE_AGENT"},
        )
        assert triggered is True

        gate = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="answer_grounding"
        ).one()
        assert gate.result == "WARNING"

        ungrounded = db.query(MonAnswerSentence).filter_by(
            request_id=REQUEST_ID, grounded=False
        ).all()
        assert len(ungrounded) >= 1
        assert "5억" in ungrounded[0].answer_sentence


    def test_grounding_matches_numbers_even_when_answer_uses_commas(self):
        grounded, agent, tool, summary = _check_grounding(
            "  · 총 이자: 2,999,991원",
            {
                "MOCK_RATE_SIMULATION": {
                    "agent": "RATE_AGENT",
                    "data_text": '{"total_interest": 2999991, "total_payment": 32999991}',
                    "summary": "총 이자 및 총 상환금액",
                }
            },
        )

        assert grounded is True
        assert agent == "RATE_AGENT"
        assert tool == "MOCK_RATE_SIMULATION"
        assert summary == "총 이자 및 총 상환금액"


class TestFinalizeTrace:
    def test_finalize_completed(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        MonitoringService.finalize_trace(
            db, REQUEST_ID, "completed", 1850, "금리 조회"
        )
        trace = db.query(MonAgentTrace).filter_by(request_id=REQUEST_ID).one()
        assert trace.status == "completed"
        assert trace.total_latency_ms == 1850
        assert trace.normalized_query == "금리 조회"

    def test_finalize_blocked(self, db):
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "테스트")
        MonitoringService.finalize_trace(db, REQUEST_ID, "blocked", 500)
        trace = db.query(MonAgentTrace).filter_by(request_id=REQUEST_ID).one()
        assert trace.status == "blocked"


# ══════════════════════════════════════════════════════════════════════════
# 전체 파이프라인 시뮬레이션 통합 테스트
# ══════════════════════════════════════════════════════════════════════════

class TestFullPipelineSimulation:
    """실제 Leader Agent 없이 MonitoringService 전체 흐름을 시뮬레이션한다."""

    class _MockResult:
        def __init__(self, api_id, status, data):
            self.api_id = api_id
            self.status = status
            self.data = data

    def test_normal_flow_all_gates_pass(self, db):
        """정상 요청: Gate 1·2·3 모두 PASS, status=completed"""
        # 0. 헤더
        MonitoringService.create_trace(db, REQUEST_ID, "user_001", "sess_001",
                                       "개인신용대출 금리 알려줘")
        # 1. Concept (정상)
        g1 = MonitoringService.save_concept_detections_and_gate1(
            db, REQUEST_ID, CONCEPT_ROWS_NORMAL
        )
        # 2. Routing (선택 있음)
        g2 = MonitoringService.save_routing_decisions_and_gate2(
            db, REQUEST_ID, AGENT_SELECTION_ROWS, ["RATE_AGENT", "POLICY_AGENT"]
        )
        # 3. Tool 실행
        MonitoringService.save_tool_execution(
            db, REQUEST_ID, "RATE_AGENT", "MOCK_RATE_LOOKUP",
            {"concept_ids": ["CONCEPT_INTEREST_RATE"]},
            "금리: 4.2% ~ 9.8%", "success", 320,
        )
        # 4. 의미분석
        MonitoringService.save_intent_analysis(
            db, REQUEST_ID, INTENT_DATA,
            ["CONCEPT_INTEREST_RATE", "CONCEPT_PERSONAL_CREDIT_LOAN"],
            ["CONCEPT_INTEREST_RATE", "CONCEPT_PERSONAL_CREDIT_LOAN"],
            ["RATE_AGENT", "POLICY_AGENT"],
        )
        # 5. 답변 근거
        raw = [self._MockResult("MOCK_RATE_LOOKUP", "success",
                                {"rates": [{"min_final_rate": "4.2", "max_final_rate": "9.8"}]})]
        g3 = MonitoringService.save_answer_sentences_and_gate3(
            db, REQUEST_ID, "■ 금리 안내\n  · 직장인 신용대출: 4.2% ~ 9.8%",
            raw, {"MOCK_RATE_LOOKUP": "RATE_AGENT"},
        )
        # 6. 마무리
        status = (
            "blocked" if g2 else "warning" if (g1 or g3) else "completed"
        )
        MonitoringService.finalize_trace(db, REQUEST_ID, status, 2000)

        assert g1 is False
        assert g2 is False
        assert g3 is False
        trace = db.query(MonAgentTrace).filter_by(request_id=REQUEST_ID).one()
        assert trace.status == "completed"

        gates = db.query(MonGateCheck).filter_by(request_id=REQUEST_ID).all()
        assert all(g.result == "PASS" for g in gates)

    def test_gate2_blocked_flow(self, db):
        """라우팅 실패: Gate 2 BLOCKED, status=blocked"""
        MonitoringService.create_trace(db, REQUEST_ID, None, None, "알 수 없는 질의")

        all_excluded = [
            {**row, "selected": False, "matched_concepts": [],
             "reason": None, "rejection_reason": "매핑 없음"}
            for row in AGENT_SELECTION_ROWS
        ]
        MonitoringService.save_concept_detections_and_gate1(db, REQUEST_ID, [])
        g2 = MonitoringService.save_routing_decisions_and_gate2(
            db, REQUEST_ID, all_excluded, []
        )
        MonitoringService.save_intent_analysis(
            db, REQUEST_ID, INTENT_DATA, [], [], []
        )
        MonitoringService.save_answer_sentences_and_gate3(
            db, REQUEST_ID,
            "요청하신 정보를 조회할 수 없었습니다. 다시 시도해 주세요.",
            [],
        )
        MonitoringService.finalize_trace(db, REQUEST_ID, "blocked", 800)

        assert g2 is True
        trace = db.query(MonAgentTrace).filter_by(request_id=REQUEST_ID).one()
        assert trace.status == "blocked"

        gate2 = db.query(MonGateCheck).filter_by(
            request_id=REQUEST_ID, gate_name="agent_routing"
        ).one()
        assert gate2.result == "BLOCKED"
