# memory_decision.py — Memory Save Decision 로직
#
# [역할]
#   FinalAnswer + ValidationResult 기반으로 단기/장기 메모리 저장 여부를 자동 판단한다.
#
# [저장 정책]
#   Short Memory (Redis, 1시간 TTL)
#     - 기본 저장
#     - V009 scope violation → 차단 (업무 범위 초과 답변은 대화 이력에 남기지 않는다)
#
#   Long-term Memory (DB, 영구)
#     - 아래 조건 중 하나라도 해당되면 저장 차단
#       1) overall_passed=False (critical 검증 실패)
#       2) V008 PII 감지 — 마스킹 후에도 원본이 민감 데이터임
#       3) V009 업무 범위 초과 — 잘못된 답변을 장기 학습 데이터로 사용 금지
#       4) MOCK_RATE_SIMULATION / MOCK_ELIGIBILITY_CHECK 사용 — 소득·자격 시뮬레이션 결과
#       5) 답변 내 소득/자산 키워드 감지

import re
from dataclasses import dataclass, field


@dataclass
class MemorySaveDecision:
    """메모리 저장 여부 판단 결과."""
    short_memory_save: bool    # Redis 단기 메모리에 저장할지 여부
    long_term_save: bool       # DB 장기 메모리에 저장할지 여부
    masking_applied: bool      # PII 마스킹이 적용된 답변을 저장하는지 여부
    reason: str                # 판단 요약 메시지
    blocked_reasons: list[str] = field(default_factory=list)  # 차단 사유 목록


# ─────────────────────────────────────────────────────────────
# 상수 정의
# ─────────────────────────────────────────────────────────────

# Long-term 저장 금지 API ID
# - RATE_SIMULATION: 월납입액 시뮬레이션에 소득/대출금액 입력값이 포함됨
# - ELIGIBILITY_CHECK: 신청 자격 확인 = 소득·자산 기준 평가 결과
_LTM_BLOCKED_APIS: frozenset[str] = frozenset({
    "MOCK_RATE_SIMULATION",
    "MOCK_ELIGIBILITY_CHECK",
})

# 답변 내 소득·자산 관련 민감 키워드 패턴
# Long-term 저장 여부 판단에 사용하는 추가 휴리스틱
SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"소득"),
    re.compile(r"연봉"),
    re.compile(r"월급"),
    re.compile(r"연소득"),
    re.compile(r"월소득"),
    re.compile(r"자산"),
    re.compile(r"재산"),
    re.compile(r"신용등급"),
]

# Critical check ID → Long-term 저장 차단 트리거
_LTM_BLOCKING_CHECKS: frozenset[str] = frozenset({"V008", "V009"})

# Critical check ID → Short-term 저장 차단 트리거 (범위 초과 답변)
_SHORT_MEMORY_BLOCKING_CHECKS: frozenset[str] = frozenset({"V009"})


# ─────────────────────────────────────────────────────────────
# 판단 로직
# ─────────────────────────────────────────────────────────────

def _has_sensitive_content(answer: str) -> bool:
    return any(p.search(answer) for p in SENSITIVE_PATTERNS)


def decide_memory_save(
    *,
    answer: str,
    risk_flags: list[str],
    overall_passed: bool,
    blocking_reason: str | None = None,
    used_api_ids: list[str],
) -> MemorySaveDecision:
    """
    FinalAnswer + ValidationResult 기반으로 메모리 저장 여부를 판단한다.

    Args:
        answer          : 최종 답변 텍스트 (PII 마스킹 후)
        risk_flags      : ValidationResult.risk_flags (실패한 check_id 목록)
        overall_passed  : ValidationResult.overall_passed
        blocking_reason : ValidationResult.blocking_reason
        used_api_ids    : 실제 호출된 API ID 목록 (StepResult.api_id 의 리스트)
    """
    blocked_reasons: list[str] = []
    masking_applied = "V008" in risk_flags

    # ── Short Memory 판단 ────────────────────────────────────────
    short_blocked = [cid for cid in _SHORT_MEMORY_BLOCKING_CHECKS if cid in risk_flags]
    short_memory_save = not short_blocked
    if short_blocked:
        blocked_reasons.append(f"단기 메모리 차단: {short_blocked}")

    # ── Long-term Memory 판단 ───────────────────────────────────
    ltm_blocked: list[str] = []

    # 조건 1: overall_passed=False (critical 검증 실패)
    if not overall_passed:
        ltm_blocked.append(
            f"검증 실패({blocking_reason or 'critical check'})"
        )

    # 조건 2~3: critical check ID (PII / 범위 초과)
    for cid in _LTM_BLOCKING_CHECKS:
        if cid in risk_flags and not any(cid in b for b in ltm_blocked):
            ltm_blocked.append(f"{cid} 감지")

    # 조건 4: 소득/자격 시뮬레이션 API 사용
    blocked_apis = [api for api in used_api_ids if api in _LTM_BLOCKED_APIS]
    if blocked_apis:
        ltm_blocked.append(f"민감 API 사용: {blocked_apis}")

    # 조건 5: 답변 내 소득·자산 키워드
    if _has_sensitive_content(answer):
        ltm_blocked.append("답변 내 소득/자산 키워드 감지")

    long_term_save = not ltm_blocked
    blocked_reasons.extend(ltm_blocked)

    # ── 판단 요약 메시지 ────────────────────────────────────────
    if long_term_save and short_memory_save:
        reason = "저장 기준 충족 — 단기/장기 메모리 모두 저장"
    elif short_memory_save:
        reason = f"단기 메모리만 저장 (장기 차단: {'; '.join(ltm_blocked)})"
    else:
        reason = f"메모리 저장 전체 차단: {'; '.join(blocked_reasons)}"

    return MemorySaveDecision(
        short_memory_save=short_memory_save,
        long_term_save=long_term_save,
        masking_applied=masking_applied,
        reason=reason,
        blocked_reasons=blocked_reasons,
    )
