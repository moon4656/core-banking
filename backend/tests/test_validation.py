# test_validation.py — ValidationChecker 단위 테스트
#
# DB / Redis / Mock API 의존성 없이 순수 클래스 메서드만 테스트한다.
# Phase 6 완료 기준: 10개 검증 항목 각각 + 통합 케이스 검증

import pytest

from app.agents.validator import ValidationChecker, ValidationResult


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────

def _checker() -> ValidationChecker:
    return ValidationChecker()


def _ev(api_id: str, confidence: float = 0.90) -> dict:
    return {"api_id": api_id, "evidence_id": 1, "confidence_score": confidence}


# ─────────────────────────────────────────────
# V001 — 최신성 검증
# ─────────────────────────────────────────────

def test_v001_passes_when_evidence_exists():
    result = _checker()._check_freshness([_ev("MOCK_RATE_LOOKUP")])
    assert result.passed is True
    assert result.check_id == "V001"


def test_v001_fails_when_no_evidence():
    result = _checker()._check_freshness([])
    assert result.passed is False
    assert result.risk_level == "medium"


# ─────────────────────────────────────────────
# V006 — 출처 신뢰도 검증
# ─────────────────────────────────────────────

def test_v006_passes_when_all_confidence_high():
    evs = [_ev("MOCK_RATE_LOOKUP", 0.90), _ev("MOCK_DOCUMENT_SEARCH", 0.85)]
    result = _checker()._check_source_confidence(evs)
    assert result.passed is True


def test_v006_fails_when_low_confidence():
    evs = [_ev("MOCK_RATE_LOOKUP", 0.90), _ev("MOCK_POLICY_LOOKUP", 0.60)]
    result = _checker()._check_source_confidence(evs)
    assert result.passed is False
    assert result.risk_level == "medium"
    assert "MOCK_POLICY_LOOKUP" in result.details.get("low_confidence_apis", [])


def test_v006_threshold_boundary():
    """정확히 0.70이면 통과 (미만만 실패)."""
    result = _checker()._check_source_confidence([_ev("MOCK_RATE_LOOKUP", 0.70)])
    assert result.passed is True


# ─────────────────────────────────────────────
# V007 — 환각 위험 검증
# ─────────────────────────────────────────────

def test_v007_passes_when_numbers_backed_by_evidence():
    result = _checker()._check_hallucination(
        "금리는 4.5%입니다.",
        [_ev("MOCK_RATE_LOOKUP")],
    )
    assert result.passed is True


def test_v007_fails_when_numbers_without_evidence():
    result = _checker()._check_hallucination("금리는 4.5%입니다.", [])
    assert result.passed is False
    assert result.risk_level == "high"


def test_v007_passes_when_no_numbers_and_no_evidence():
    """숫자 없는 답변 + Evidence 없음 = 환각 위험 없음."""
    result = _checker()._check_hallucination("관련 정보를 확인 중입니다.", [])
    assert result.passed is True


# ─────────────────────────────────────────────
# V008 — 개인정보/민감정보 검증 (CRITICAL)
# ─────────────────────────────────────────────

def test_v008_critical_on_rrn_pattern():
    """주민등록번호 패턴(XXXXXX-XXXXXXX) 포함 시 critical 실패 — Phase 6 완료 기준."""
    result = _checker()._check_pii("고객 주민번호는 901225-1234567입니다.")
    assert result.passed is False
    assert result.risk_level == "critical"
    assert "주민등록번호" in result.details.get("detected_pii_types", [])


def test_v008_critical_on_account_number():
    """계좌번호 패턴 포함 시 critical 실패."""
    result = _checker()._check_pii("계좌번호 110-123-456789로 이체하세요.")
    assert result.passed is False
    assert result.risk_level == "critical"
    assert "계좌번호" in result.details.get("detected_pii_types", [])


def test_v008_critical_on_phone_number():
    result = _checker()._check_pii("연락처: 010-1234-5678")
    assert result.passed is False
    assert result.risk_level == "critical"


def test_v008_passes_with_no_pii():
    result = _checker()._check_pii("신용대출 금리는 연 4.5%입니다.")
    assert result.passed is True


def test_v008_masking_applied_in_run_all():
    """run_all() 실행 시 PII가 실제로 마스킹돼야 한다."""
    answer = "주민번호 901225-1234567 확인됩니다."
    result = _checker().run_all(
        answer=answer,
        evidence_results=[_ev("MOCK_PRODUCT_LOOKUP")],
        intent="INQUIRY",
        user_role="ANALYST",
    )
    assert result.sanitized_answer is not None
    assert "901225-1234567" not in result.sanitized_answer
    assert "V008" in result.risk_flags


# ─────────────────────────────────────────────
# V009 — 답변 가능 범위 검증 (CRITICAL)
# ─────────────────────────────────────────────

def test_v009_critical_on_forbidden_keyword():
    result = _checker()._check_scope("대출 승인 처리해 드리겠습니다.", "APPLICATION")
    assert result.passed is False
    assert result.risk_level == "critical"
    assert "대출 승인" in result.details.get("forbidden_keywords", [])


def test_v009_passes_on_normal_answer():
    result = _checker()._check_scope("신용대출 금리는 4.5%입니다.", "INQUIRY")
    assert result.passed is True


# ─────────────────────────────────────────────
# V010 — 면책 안내 필요 검증
# ─────────────────────────────────────────────

def test_v010_fails_for_financial_intents():
    for intent in ["INQUIRY", "COMPARISON", "RECOMMENDATION", "APPLICATION"]:
        result = _checker()._check_disclaimer_required(intent)
        assert result.passed is False, f"Intent {intent}에서 면책 문구 필요"
        assert result.risk_level == "high"


def test_v010_passes_for_other_intent():
    result = _checker()._check_disclaimer_required("OTHER")
    assert result.passed is True


def test_v010_disclaimer_appended_in_run_all():
    """run_all() 실행 시 면책 문구가 답변 말미에 자동 삽입돼야 한다."""
    result = _checker().run_all(
        answer="금리는 4.5%입니다.",
        evidence_results=[_ev("MOCK_RATE_LOOKUP")],
        intent="INQUIRY",
        user_role="ANALYST",
    )
    assert result.requires_disclaimer is True
    assert result.sanitized_answer is not None
    assert "※ 본 안내는 참고 목적" in result.sanitized_answer


# ─────────────────────────────────────────────
# V004 — 사용자 권한 검증
# ─────────────────────────────────────────────

def test_v004_readonly_gets_medium_warning():
    result = _checker()._check_user_permission("READONLY")
    assert result.passed is False
    assert result.risk_level == "medium"


def test_v004_analyst_passes():
    result = _checker()._check_user_permission("ANALYST")
    assert result.passed is True


def test_v004_admin_passes():
    result = _checker()._check_user_permission("ADMIN")
    assert result.passed is True


# ─────────────────────────────────────────────
# 통합 — run_all()
# ─────────────────────────────────────────────

def test_run_all_overall_passed_with_no_critical():
    """critical 항목이 없으면 overall_passed=True (warning이 있어도)."""
    result = _checker().run_all(
        answer="신용대출 금리는 연 4.5%입니다.",
        evidence_results=[_ev("MOCK_RATE_LOOKUP", 0.91)],
        intent="INQUIRY",
        user_role="ANALYST",
    )
    assert result.overall_passed is True
    # INQUIRY 의도 → V010 면책 문구 포함
    assert "V010" in result.risk_flags
    assert result.requires_disclaimer is True


def test_run_all_failed_on_pii():
    """PII(critical) 감지 시 overall_passed=False."""
    result = _checker().run_all(
        answer="고객 주민번호 901225-1234567을 확인했습니다.",
        evidence_results=[_ev("MOCK_PRODUCT_LOOKUP")],
        intent="INQUIRY",
        user_role="ANALYST",
    )
    assert result.overall_passed is False
    assert result.blocking_reason is not None
    assert "V008" in result.risk_flags


def test_run_all_returns_ten_checks():
    """run_all()은 항상 10개 CheckResult를 반환해야 한다."""
    result = _checker().run_all(
        answer="금리 안내입니다.",
        evidence_results=[_ev("MOCK_RATE_LOOKUP")],
        intent="INQUIRY",
        user_role="ANALYST",
    )
    assert len(result.check_results) == 10
    check_ids = {c.check_id for c in result.check_results}
    expected = {f"V{str(i).zfill(3)}" for i in range(1, 11)}
    assert check_ids == expected
