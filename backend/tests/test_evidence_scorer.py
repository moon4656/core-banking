# test_evidence_scorer.py — evidence_scorer.py 단위 테스트
#
# DB / Redis / Mock API 의존성 없이 순수 함수만 테스트한다.
# score_evidence() 공식:  0.5 × data_quality + 0.4 × intent_relevance + 0.1 × latency
#
# [실행]
#   docker compose exec backend pytest tests/test_evidence_scorer.py -v

import pytest

from app.schemas.decision_trace import AnswerSlot
from app.trace.evidence_scorer import (
    EvidenceScore,
    _score_intent_relevance,
    _score_latency,
    rank_evidence_by_slots,
    score_evidence,
)


# ─────────────────────────────────────────────
# latency 점수
# ─────────────────────────────────────────────

def test_latency_fast():
    assert _score_latency(500)   == 1.0
    assert _score_latency(2000)  == 1.0


def test_latency_medium():
    assert _score_latency(2001)  == 0.8
    assert _score_latency(5000)  == 0.8


def test_latency_slow():
    assert _score_latency(5001)  == 0.5
    assert _score_latency(30000) == 0.5


# ─────────────────────────────────────────────
# intent relevance 점수
# ─────────────────────────────────────────────

def test_intent_relevance_known():
    assert _score_intent_relevance("MOCK_RATE_LOOKUP", "INQUIRY")     == 1.0
    assert _score_intent_relevance("MOCK_RATE_LOOKUP", "COMPARISON")  == 1.0
    assert _score_intent_relevance("MOCK_DOCUMENT_SEARCH", "APPLICATION") == 1.0
    assert _score_intent_relevance("MOCK_BRANCH_LOOKUP", "COMPARISON") == 0.1


def test_intent_relevance_unknown_intent_falls_back_to_other():
    score = _score_intent_relevance("MOCK_RATE_LOOKUP", "UNKNOWN_INTENT")
    assert score == 0.5  # OTHER 테이블 기본값


def test_intent_relevance_unknown_api_falls_back_to_default():
    score = _score_intent_relevance("MOCK_NONEXISTENT_API", "INQUIRY")
    assert score == 0.5


# ─────────────────────────────────────────────
# score_evidence — 정상 데이터
# ─────────────────────────────────────────────

def test_score_evidence_rate_lookup_comparison():
    """
    MOCK_RATE_LOOKUP + COMPARISON 의도 + 빠른 응답
    data_quality: 8개 항목, 필수 필드 3/3 커버리지=1.0
      count_bonus = min(8/10, 0.4) = 0.4
      score = 0.6*1.0 + 0.4 = 1.0 → clamp 1.0
    intent_relevance: COMPARISON × RATE_LOOKUP = 1.0
    latency: 200ms → 1.0
    confidence = 0.5*1.0 + 0.4*1.0 + 0.1*1.0 = 1.0
    """
    data = {
        "rates": [
            {"product_id": f"P00{i}", "base_rate": 4.5, "rate_type": "변동금리"}
            for i in range(1, 9)
        ],
        "total": 8,
    }
    result = score_evidence("MOCK_RATE_LOOKUP", data, "COMPARISON", 200)

    assert isinstance(result, EvidenceScore)
    assert result.data_quality_score == 1.0
    assert result.intent_relevance_score == 1.0
    assert result.item_count == 8
    assert result.confidence_score == pytest.approx(1.0, abs=0.001)


def test_score_evidence_product_lookup_inquiry():
    """
    MOCK_PRODUCT_LOOKUP + INQUIRY 의도
    data: 8개 항목, 필수 필드 4/4 커버리지=1.0
      count_bonus = 0.4 → dq = 1.0
    intent_relevance: INQUIRY × PRODUCT = 0.8
    latency: 1000ms → 1.0
    confidence = 0.5*1.0 + 0.4*0.8 + 0.1*1.0 = 0.5 + 0.32 + 0.1 = 0.92
    """
    data = {
        "products": [
            {
                "product_id": f"P00{i}",
                "name": f"상품{i}",
                "min_amount": 1_000_000,
                "max_amount": 100_000_000,
            }
            for i in range(1, 9)
        ],
        "total": 8,
    }
    result = score_evidence("MOCK_PRODUCT_LOOKUP", data, "INQUIRY", 1000)

    assert result.data_quality_score == 1.0
    assert result.intent_relevance_score == 0.8
    assert result.confidence_score == pytest.approx(0.92, abs=0.001)


def test_score_evidence_document_search_application():
    """
    MOCK_DOCUMENT_SEARCH + APPLICATION 의도
    data: 13개 항목, 필수 필드 3/3 커버리지=1.0
      count_bonus = min(13/10, 0.4) = 0.4 → dq = 1.0
    intent_relevance: APPLICATION × DOCUMENT = 1.0
    latency: 800ms → 1.0
    confidence = 0.5*1.0 + 0.4*1.0 + 0.1*1.0 = 1.0
    """
    data = {
        "documents": [
            {"doc_id": f"DOC{i:03d}", "name": f"서류{i}", "category": "공통필수"}
            for i in range(1, 14)
        ],
        "total": 13,
    }
    result = score_evidence("MOCK_DOCUMENT_SEARCH", data, "APPLICATION", 800)

    assert result.data_quality_score == 1.0
    assert result.intent_relevance_score == 1.0
    assert result.confidence_score == pytest.approx(1.0, abs=0.001)


def test_score_evidence_policy_lookup():
    """
    MOCK_POLICY_LOOKUP + INQUIRY 의도
    data: 8개 항목, 필수 필드 3/3 커버리지=1.0
      count_bonus = 0.4 → dq = 1.0
    intent_relevance: INQUIRY × POLICY = 0.6
    latency: 300ms → 1.0
    confidence = 0.5*1.0 + 0.4*0.6 + 0.1*1.0 = 0.5 + 0.24 + 0.1 = 0.84
    """
    data = {
        "policies": [
            {"policy_id": f"POL{i:03d}", "policy_type": "심사기준", "detail": {"key": "val"}}
            for i in range(1, 9)
        ],
        "total": 8,
    }
    result = score_evidence("MOCK_POLICY_LOOKUP", data, "INQUIRY", 300)

    assert result.data_quality_score == 1.0
    assert result.intent_relevance_score == 0.6
    assert result.confidence_score == pytest.approx(0.84, abs=0.001)


# ─────────────────────────────────────────────
# score_evidence — 엣지 케이스
# ─────────────────────────────────────────────

def test_score_evidence_no_data():
    """data=None 이면 모든 점수 0."""
    result = score_evidence("MOCK_RATE_LOOKUP", None, "INQUIRY", 100)

    assert result.confidence_score == 0.0
    assert result.data_quality_score == 0.0
    assert result.intent_relevance_score == 0.0
    assert result.item_count == 0


def test_score_evidence_empty_list():
    """빈 목록이면 data_quality 0.1 (empty_list 페널티)."""
    data = {"rates": [], "total": 0}
    result = score_evidence("MOCK_RATE_LOOKUP", data, "INQUIRY", 100)

    assert result.data_quality_score == pytest.approx(0.1, abs=0.001)
    assert result.item_count == 0
    assert result.quality_flags.get("empty_list") is True


def test_score_evidence_missing_critical_field_penalty():
    """
    필수 수치 필드(base_rate)가 None 이면 -0.2 페널티.
    1개 항목, 커버리지: product_id✓ base_rate(None)✗ rate_type✓ → 2/3 = 0.667
    count_bonus = min(1/10, 0.4) = 0.1
    score_before_penalty = 0.6*0.667 + 0.1 = 0.5
    null_critical=[base_rate] → score -= 0.2 → 0.3
    """
    data = {
        "rates": [{"product_id": "P001", "base_rate": None, "rate_type": "변동금리"}],
        "total": 1,
    }
    result = score_evidence("MOCK_RATE_LOOKUP", data, "INQUIRY", 100)

    assert result.quality_flags.get("null_critical_fields") == ["base_rate"]
    assert result.data_quality_score == pytest.approx(0.3, abs=0.01)


def test_score_evidence_slow_latency_penalty():
    """
    5초 초과 응답 시 latency_bonus=0.5, 최종 confidence 낮아짐.
    MOCK_RATE_LOOKUP + INQUIRY, 1개 항목 완전한 데이터
      coverage = 1.0 (product_id, base_rate, rate_type 모두 존재)
      count_bonus = min(1/10, 0.4) = 0.1
      dq = 0.6*1.0 + 0.1 = 0.7
    ir = 1.0 (INQUIRY × RATE_LOOKUP)
    latency = 0.5 (6000ms > 5000ms)
    confidence = 0.5*0.7 + 0.4*1.0 + 0.1*0.5 = 0.35 + 0.40 + 0.05 = 0.80
    """
    data = {
        "rates": [
            {"product_id": "P001", "base_rate": 4.5, "rate_type": "변동금리"}
        ],
        "total": 1,
    }
    result = score_evidence("MOCK_RATE_LOOKUP", data, "INQUIRY", 6000)

    assert result.data_quality_score == pytest.approx(0.7, abs=0.01)
    assert result.confidence_score == pytest.approx(0.80, abs=0.01)


def test_score_evidence_unknown_api_uses_default_score():
    """스펙 정의 없는 API는 data_quality 기본값 0.7."""
    data = {"custom_field": "value"}
    result = score_evidence("MOCK_CUSTOM_API", data, "INQUIRY", 500)

    assert result.data_quality_score == pytest.approx(0.7, abs=0.001)
    assert result.quality_flags.get("spec_defined") is False


# ─────────────────────────────────────────────
# Phase 5 — Answer Slot Ranking
# ─────────────────────────────────────────────

def _make_slot(slot_name: str, label_ko: str, tools: list[str]) -> AnswerSlot:
    return AnswerSlot(slot_name=slot_name, label_ko=label_ko, tools=tools)


def test_rank_evidence_interest_rate_slot_prefers_rate_lookup():
    """
    interest_rate 슬롯에 RATE_LOOKUP Evidence가 있으면 1순위로 선택돼야 한다.
    완료 기준: interest_rate slot → MOCK_RATE_LOOKUP이 1순위
    """
    slots = [_make_slot("interest_rate", "금리", ["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"])]
    evidence_results = [
        {"api_id": "MOCK_RATE_LOOKUP",     "evidence_id": 1, "confidence_score": 0.92},
        {"api_id": "MOCK_RATE_SIMULATION", "evidence_id": 2, "confidence_score": 0.75},
        {"api_id": "MOCK_PRODUCT_LOOKUP",  "evidence_id": 3, "confidence_score": 0.88},  # 슬롯 무관
    ]

    rankings = rank_evidence_by_slots(slots, evidence_results)

    assert len(rankings) == 1
    ranking = rankings[0]
    assert ranking.slot_name == "interest_rate"
    assert ranking.slot_filled is True
    assert ranking.best_evidence is not None
    assert ranking.best_evidence.api_id == "MOCK_RATE_LOOKUP"
    assert ranking.best_evidence.rank == 1
    assert len(ranking.candidates) == 2


def test_rank_evidence_compound_query_two_slots():
    """
    "금리와 서류 알려줘" 질문 → interest_rate, required_document 두 슬롯이 각각 채워져야 한다.
    """
    slots = [
        _make_slot("interest_rate",    "금리",    ["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"]),
        _make_slot("required_document", "필요서류", ["MOCK_DOCUMENT_SEARCH", "MOCK_POLICY_LOOKUP"]),
    ]
    evidence_results = [
        {"api_id": "MOCK_RATE_LOOKUP",    "evidence_id": 1, "confidence_score": 0.91},
        {"api_id": "MOCK_DOCUMENT_SEARCH","evidence_id": 2, "confidence_score": 0.85},
    ]

    rankings = rank_evidence_by_slots(slots, evidence_results)

    assert len(rankings) == 2

    rate_ranking = next(r for r in rankings if r.slot_name == "interest_rate")
    assert rate_ranking.slot_filled is True
    assert rate_ranking.best_evidence.api_id == "MOCK_RATE_LOOKUP"

    doc_ranking = next(r for r in rankings if r.slot_name == "required_document")
    assert doc_ranking.slot_filled is True
    assert doc_ranking.best_evidence.api_id == "MOCK_DOCUMENT_SEARCH"


def test_rank_evidence_unfilled_slot_when_no_matching_tool():
    """
    슬롯에 연결된 Tool의 Evidence가 없으면 slot_filled=False여야 한다.
    """
    slots = [_make_slot("counseling_history", "상담이력", ["MOCK_COUNSELING_HISTORY"])]
    evidence_results = [
        {"api_id": "MOCK_RATE_LOOKUP", "evidence_id": 1, "confidence_score": 0.9},
    ]

    rankings = rank_evidence_by_slots(slots, evidence_results)

    assert len(rankings) == 1
    assert rankings[0].slot_filled is False
    assert rankings[0].best_evidence is None
    assert rankings[0].candidates == []


def test_rank_evidence_empty_slots_returns_empty():
    """슬롯 목록이 비어 있으면 빈 리스트를 반환해야 한다."""
    rankings = rank_evidence_by_slots([], [{"api_id": "MOCK_RATE_LOOKUP", "evidence_id": 1, "confidence_score": 0.9}])
    assert rankings == []


def test_rank_evidence_candidate_order_by_confidence():
    """
    같은 슬롯에 후보가 여러 개이면 confidence_score 내림차순으로 정렬돼야 한다.
    """
    slots = [_make_slot("interest_rate", "금리", ["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"])]
    evidence_results = [
        {"api_id": "MOCK_RATE_SIMULATION", "evidence_id": 2, "confidence_score": 0.99},
        {"api_id": "MOCK_RATE_LOOKUP",     "evidence_id": 1, "confidence_score": 0.75},
    ]

    rankings = rank_evidence_by_slots(slots, evidence_results)
    ranking = rankings[0]

    assert ranking.best_evidence.api_id == "MOCK_RATE_SIMULATION"
    assert ranking.candidates[0].rank == 1
    assert ranking.candidates[1].rank == 2
    assert ranking.candidates[0].confidence_score > ranking.candidates[1].confidence_score
