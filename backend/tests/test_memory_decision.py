# test_memory_decision.py — Memory Save Decision 단위 테스트
#
# DB / Redis / Mock API 의존성 없이 순수 함수만 테스트한다.
# Phase 7 완료 기준: RATE_SIMULATION 결과(소득 포함) 시 Long-term 저장 차단 확인

import pytest

from app.agents.memory_decision import MemorySaveDecision, decide_memory_save


# ─────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────

def _decide(
    answer: str = "금리는 4.5%입니다.",
    risk_flags: list[str] | None = None,
    overall_passed: bool = True,
    blocking_reason: str | None = None,
    used_api_ids: list[str] | None = None,
) -> MemorySaveDecision:
    return decide_memory_save(
        answer=answer,
        risk_flags=risk_flags or [],
        overall_passed=overall_passed,
        blocking_reason=blocking_reason,
        used_api_ids=used_api_ids or [],
    )


# ─────────────────────────────────────────────────────────────
# 정상 저장 케이스
# ─────────────────────────────────────────────────────────────

def test_normal_answer_saves_both():
    """검증 통과 + 민감 API 없음 → 단기/장기 모두 저장."""
    result = _decide(
        answer="신용대출 금리는 연 4.5%입니다.",
        used_api_ids=["MOCK_RATE_LOOKUP", "MOCK_PRODUCT_LOOKUP"],
    )
    assert result.short_memory_save is True
    assert result.long_term_save is True
    assert result.masking_applied is False


# ─────────────────────────────────────────────────────────────
# Long-term 저장 차단 — RATE_SIMULATION (Phase 7 완료 기준)
# ─────────────────────────────────────────────────────────────

def test_rate_simulation_blocks_long_term_save():
    """
    MOCK_RATE_SIMULATION 사용 시 Long-term 저장 차단.
    Phase 7 완료 기준: RATE_SIMULATION 결과(소득 포함) 시 Long-term 저장 차단 확인
    """
    result = _decide(
        answer="월납입액은 약 850,000원으로 예상됩니다.",
        used_api_ids=["MOCK_RATE_SIMULATION"],
    )
    assert result.long_term_save is False
    assert result.short_memory_save is True  # 단기 메모리는 허용
    assert any("MOCK_RATE_SIMULATION" in r for r in result.blocked_reasons)


def test_eligibility_check_blocks_long_term_save():
    """MOCK_ELIGIBILITY_CHECK 사용 시 Long-term 저장 차단."""
    result = _decide(
        answer="신청 자격이 확인되었습니다.",
        used_api_ids=["MOCK_ELIGIBILITY_CHECK"],
    )
    assert result.long_term_save is False
    assert result.short_memory_save is True


def test_mixed_apis_blocks_long_term_when_sensitive_api_included():
    """민감 API가 일반 API와 함께 사용되어도 Long-term 차단."""
    result = _decide(
        answer="금리 및 시뮬레이션 결과입니다.",
        used_api_ids=["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"],
    )
    assert result.long_term_save is False
    assert result.short_memory_save is True


# ─────────────────────────────────────────────────────────────
# Long-term 저장 차단 — 답변 내 민감 키워드
# ─────────────────────────────────────────────────────────────

def test_income_keyword_in_answer_blocks_long_term():
    """답변에 '소득' 키워드 포함 → Long-term 차단."""
    result = _decide(
        answer="연소득 5천만원 기준으로 최대 대출 한도는 1억원입니다.",
        used_api_ids=["MOCK_PRODUCT_LOOKUP"],
    )
    assert result.long_term_save is False
    assert result.short_memory_save is True
    assert any("소득/자산" in r for r in result.blocked_reasons)


def test_salary_keyword_blocks_long_term():
    result = _decide(answer="월급이 300만원 이상이면 신청 가능합니다.")
    assert result.long_term_save is False


def test_asset_keyword_blocks_long_term():
    result = _decide(answer="자산이 2억원 이상인 경우 우대금리를 적용받습니다.")
    assert result.long_term_save is False


def test_credit_grade_keyword_blocks_long_term():
    result = _decide(answer="신용등급 1~3등급이면 금리 우대 혜택이 있습니다.")
    assert result.long_term_save is False


# ─────────────────────────────────────────────────────────────
# Long-term 저장 차단 — PII (V008)
# ─────────────────────────────────────────────────────────────

def test_pii_flag_blocks_long_term():
    """V008 PII 감지 시 Long-term 저장 차단 + masking_applied=True."""
    result = _decide(
        answer="######-####### (마스킹됨)",  # 이미 마스킹된 답변
        risk_flags=["V008"],
        overall_passed=False,
        blocking_reason="PII 패턴 감지",
    )
    assert result.long_term_save is False
    assert result.masking_applied is True


def test_pii_flag_masking_applied():
    """V008만 있으면 masking_applied=True."""
    result = _decide(
        answer="연 4.5% 금리입니다.",
        risk_flags=["V008"],
        overall_passed=False,
    )
    assert result.masking_applied is True


# ─────────────────────────────────────────────────────────────
# Short Memory 차단 — V009 scope violation
# ─────────────────────────────────────────────────────────────

def test_scope_violation_blocks_short_memory():
    """V009 scope violation → 단기 메모리도 차단."""
    result = _decide(
        answer="대출 승인 처리해 드리겠습니다.",
        risk_flags=["V009"],
        overall_passed=False,
        blocking_reason="업무 범위 초과",
    )
    assert result.short_memory_save is False
    assert result.long_term_save is False
    assert any("V009" in r for r in result.blocked_reasons)


# ─────────────────────────────────────────────────────────────
# overall_passed=False → Long-term 차단
# ─────────────────────────────────────────────────────────────

def test_overall_failed_blocks_long_term():
    """overall_passed=False → Long-term 차단 (short은 V009 없으면 저장)."""
    result = _decide(
        answer="금리 안내입니다.",
        risk_flags=["V008"],
        overall_passed=False,
        blocking_reason="PII 패턴 감지",
    )
    assert result.long_term_save is False
    assert result.short_memory_save is True  # V009 없으므로 단기는 저장


# ─────────────────────────────────────────────────────────────
# masking_applied — V008 있을 때만 True
# ─────────────────────────────────────────────────────────────

def test_masking_not_applied_without_v008():
    """V008 없으면 masking_applied=False."""
    result = _decide(risk_flags=["V006"])
    assert result.masking_applied is False


def test_masking_applied_with_v008():
    """V008 있으면 masking_applied=True."""
    result = _decide(risk_flags=["V008"], overall_passed=False)
    assert result.masking_applied is True


# ─────────────────────────────────────────────────────────────
# blocked_reasons 포함 여부
# ─────────────────────────────────────────────────────────────

def test_blocked_reasons_populated_on_ltm_block():
    """장기 차단 시 blocked_reasons에 사유가 포함돼야 한다."""
    result = _decide(
        used_api_ids=["MOCK_RATE_SIMULATION"],
    )
    assert len(result.blocked_reasons) > 0


def test_blocked_reasons_empty_on_full_save():
    """모두 저장되면 blocked_reasons는 비어야 한다."""
    result = _decide(
        answer="금리는 4.5%입니다.",
        used_api_ids=["MOCK_RATE_LOOKUP"],
    )
    assert result.blocked_reasons == []


# ─────────────────────────────────────────────────────────────
# reason 메시지 형식
# ─────────────────────────────────────────────────────────────

def test_reason_contains_blocked_api_name():
    result = _decide(used_api_ids=["MOCK_RATE_SIMULATION"])
    assert "MOCK_RATE_SIMULATION" in result.reason


def test_reason_indicates_full_save():
    result = _decide(
        answer="금리 안내입니다.",
        used_api_ids=["MOCK_RATE_LOOKUP"],
    )
    assert "모두 저장" in result.reason
