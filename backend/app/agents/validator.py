# validator.py — 답변 품질/안전 검증 파이프라인
#
# [역할]
#   Leader Agent가 최종 답변을 생성한 직후 10개 항목을 검증한다.
#   통과/실패 여부, 위험 플래그, 수행된 조치를 ValidationResult로 반환한다.
#
# [실패 처리 방식]
#   risk_level="critical" → 답변 전송 차단 (blocking)
#   risk_level="high"     → 면책 문구 자동 삽입
#   risk_level="medium"   → 경고 플래그만 기록
#   risk_level="low"      → 참고 기록만

import re
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    """단일 검증 항목 결과."""
    check_id:    str
    check_name:  str
    passed:      bool
    risk_level:  str           # "low" | "medium" | "high" | "critical"
    message:     str | None = None
    action_taken: str | None = None
    details:     dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """
    전체 검증 파이프라인 결과.

    overall_passed   : critical 항목이 하나도 없으면 True
    sanitized_answer : PII 마스킹 + 면책 문구 삽입 후 답변. 원본과 동일하면 None.
    blocking_reason  : overall_passed=False 원인 메시지
    """
    overall_passed:    bool
    check_results:     list[CheckResult]
    risk_flags:        list[str]      # 실패한 check_id 목록
    actions_taken:     list[str]      # 수행된 조치 설명 목록
    sanitized_answer:  str | None = None
    requires_disclaimer: bool = False
    blocking_reason:   str | None = None


# ─────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────

_DISCLAIMER_TEXT = (
    "\n\n※ 본 안내는 참고 목적이며, 실제 금융 상품 조건은 영업점 또는 공식 앱에서 반드시 확인하시기 바랍니다."
)

_DISCLAIMER_INTENTS = {"INQUIRY", "COMPARISON", "RECOMMENDATION", "APPLICATION"}

_FORBIDDEN_SCOPE_KEYWORDS = [
    "대출 승인", "대출승인", "즉시 실행", "즉시실행",
    "계좌 이체", "계좌이체", "실거래", "실제 대출",
]

_LOW_CONFIDENCE_THRESHOLD = 0.70

# PII 정규식: (pattern, 항목명)
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\d{6}-[1-4]\d{6}"),            "주민등록번호"),
    (re.compile(r"\d{3}-\d{2,3}-\d{6,7}"),       "계좌번호"),
    (re.compile(r"01[016789]-\d{3,4}-\d{4}"),    "전화번호"),
    (re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE), "이메일"),
]

# PII 마스킹 치환 패턴 (원본 값을 ***로 대체)
_PII_MASK_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\d{6}-[1-4]\d{6}"),            "######-#######"),
    (re.compile(r"\d{3}-\d{2,3}-\d{6,7}"),       "***-***-*****"),
    (re.compile(r"01[016789]-\d{3,4}-\d{4}"),    "***-****-****"),
    (re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE), "***@***.***"),
]

# 숫자(소수점 포함) 추출 패턴
_NUMBER_PATTERN = re.compile(r"\d+\.?\d*")


class ValidationChecker:
    """
    10개 항목 검증을 순차 실행하고 ValidationResult를 반환한다.

    run_all()을 호출하면 내부적으로 각 check 메서드를 실행한다.
    check 메서드는 독립적이므로 순서는 결과에 영향을 주지 않는다.
    """

    def run_all(
        self,
        *,
        answer: str,
        evidence_results: list[dict],
        intent: str,
        user_role: str,
    ) -> ValidationResult:
        """
        10개 검증 항목을 실행하고 ValidationResult를 반환한다.

        Args:
            answer           : LLM이 생성한 최종 답변 텍스트
            evidence_results : [{"api_id", "evidence_id", "confidence_score"}] 경량 Evidence
            intent           : 사용자 의도 ("INQUIRY" | "COMPARISON" | ...)
            user_role        : 요청 사용자 역할 ("ADMIN" | "ANALYST" | "READONLY")
        """
        checks = [
            self._check_pii(answer),                            # V008 먼저 — critical
            self._check_scope(answer, intent),                  # V009 — critical
            self._check_freshness(evidence_results),            # V001
            self._check_policy_version(evidence_results),       # V002
            self._check_rate_validity(evidence_results),        # V003
            self._check_user_permission(user_role),             # V004
            self._check_document_access(user_role),             # V005
            self._check_source_confidence(evidence_results),    # V006
            self._check_hallucination(answer, evidence_results),# V007
            self._check_disclaimer_required(intent),            # V010
        ]

        risk_flags = [c.check_id for c in checks if not c.passed]
        actions: list[str] = []

        sanitized = answer

        # PII 마스킹 적용 (V008 failed)
        pii_failed = any(c.check_id == "V008" and not c.passed for c in checks)
        if pii_failed:
            sanitized = self._apply_pii_masking(sanitized)
            actions.append("PII 마스킹 적용 (주민번호/계좌번호 패턴 제거)")

        # 면책 문구 삽입 (V010 failed)
        disclaimer_needed = any(c.check_id == "V010" and not c.passed for c in checks)
        if disclaimer_needed and _DISCLAIMER_TEXT not in sanitized:
            sanitized += _DISCLAIMER_TEXT
            actions.append("면책 안내 문구 자동 삽입")

        for c in checks:
            if c.action_taken:
                actions.append(c.action_taken)

        # overall_passed: critical 항목 없으면 True
        blocking = [c for c in checks if not c.passed and c.risk_level == "critical"]
        overall_passed = len(blocking) == 0

        return ValidationResult(
            overall_passed=overall_passed,
            check_results=checks,
            risk_flags=risk_flags,
            actions_taken=actions,
            sanitized_answer=sanitized if sanitized != answer else None,
            requires_disclaimer=disclaimer_needed,
            blocking_reason=blocking[0].message if blocking else None,
        )

    # ─────────────────────────────────────────────────────────
    # V001 — 최신성 검증
    # ─────────────────────────────────────────────────────────
    def _check_freshness(self, evidence_results: list[dict]) -> CheckResult:
        """Evidence가 전혀 없으면 데이터 신선도를 보장할 수 없다."""
        if not evidence_results:
            return CheckResult(
                check_id="V001",
                check_name="최신성 검증",
                passed=False,
                risk_level="medium",
                message="수집된 Evidence 없음 — 최신 데이터 보장 불가",
                action_taken="'최신 정보를 공식 채널에서 확인하세요' 안내 권장",
            )
        return CheckResult(
            check_id="V001",
            check_name="최신성 검증",
            passed=True,
            risk_level="low",
            message="Evidence 데이터 수집 확인",
        )

    # ─────────────────────────────────────────────────────────
    # V002 — 정책 버전 검증
    # ─────────────────────────────────────────────────────────
    def _check_policy_version(self, evidence_results: list[dict]) -> CheckResult:
        """MVP: Mock API는 버전 메타데이터를 제공하지 않으므로 항상 통과."""
        return CheckResult(
            check_id="V002",
            check_name="정책 버전 검증",
            passed=True,
            risk_level="low",
            message="MVP — 정책 버전 메타데이터 없음, 자동 통과",
        )

    # ─────────────────────────────────────────────────────────
    # V003 — 금리 유효일 검증
    # ─────────────────────────────────────────────────────────
    def _check_rate_validity(self, evidence_results: list[dict]) -> CheckResult:
        """MVP: Mock API는 reference_date를 제공하지 않으므로 항상 통과."""
        has_rate_evidence = any(
            ev.get("api_id") in ("MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION")
            for ev in evidence_results
        )
        if not has_rate_evidence:
            return CheckResult(
                check_id="V003",
                check_name="금리 유효일 검증",
                passed=True,
                risk_level="low",
                message="금리 Evidence 없음 — 해당 없음",
            )
        return CheckResult(
            check_id="V003",
            check_name="금리 유효일 검증",
            passed=True,
            risk_level="low",
            message="MVP — 금리 유효일 메타데이터 없음, 자동 통과",
        )

    # ─────────────────────────────────────────────────────────
    # V004 — 사용자 권한 검증
    # ─────────────────────────────────────────────────────────
    def _check_user_permission(self, user_role: str) -> CheckResult:
        """READONLY 사용자는 금융 상품 상세 조회 권한이 제한된다."""
        role_upper = (user_role or "").upper()
        if role_upper == "READONLY":
            return CheckResult(
                check_id="V004",
                check_name="사용자 권한 검증",
                passed=False,
                risk_level="medium",
                message="READONLY 역할 — 금융 상품 상세 정보 조회 권한 제한",
                details={"user_role": user_role},
            )
        return CheckResult(
            check_id="V004",
            check_name="사용자 권한 검증",
            passed=True,
            risk_level="low",
            message=f"권한 확인: {role_upper}",
            details={"user_role": user_role},
        )

    # ─────────────────────────────────────────────────────────
    # V005 — 문서 접근 권한 검증
    # ─────────────────────────────────────────────────────────
    def _check_document_access(self, user_role: str) -> CheckResult:
        """MVP: Mock API는 문서 접근 레벨을 제공하지 않으므로 항상 통과."""
        return CheckResult(
            check_id="V005",
            check_name="문서 접근 권한 검증",
            passed=True,
            risk_level="low",
            message="MVP — 문서 접근 레벨 메타데이터 없음, 자동 통과",
        )

    # ─────────────────────────────────────────────────────────
    # V006 — 출처 신뢰도 검증
    # ─────────────────────────────────────────────────────────
    def _check_source_confidence(self, evidence_results: list[dict]) -> CheckResult:
        """Evidence 신뢰도 점수가 0.70 미만이면 경고."""
        low_conf = [
            ev for ev in evidence_results
            if ev.get("confidence_score", 1.0) < _LOW_CONFIDENCE_THRESHOLD
        ]
        if low_conf:
            ids = [ev.get("api_id") for ev in low_conf]
            return CheckResult(
                check_id="V006",
                check_name="출처 신뢰도 검증",
                passed=False,
                risk_level="medium",
                message=f"신뢰도 낮은 Evidence {len(low_conf)}건: {ids}",
                details={"low_confidence_apis": ids, "threshold": _LOW_CONFIDENCE_THRESHOLD},
            )
        return CheckResult(
            check_id="V006",
            check_name="출처 신뢰도 검증",
            passed=True,
            risk_level="low",
            message=f"전체 Evidence 신뢰도 ≥ {_LOW_CONFIDENCE_THRESHOLD}",
        )

    # ─────────────────────────────────────────────────────────
    # V007 — 환각 위험 검증
    # ─────────────────────────────────────────────────────────
    def _check_hallucination(
        self,
        answer: str,
        evidence_results: list[dict],
    ) -> CheckResult:
        """
        답변에 숫자가 포함됐는데 Evidence가 없으면 환각 위험으로 판단한다.

        MVP 수준 휴리스틱: 데이터 없이 숫자를 언급하면 잠재적 환각.
        """
        answer_numbers = _NUMBER_PATTERN.findall(answer)
        if answer_numbers and not evidence_results:
            return CheckResult(
                check_id="V007",
                check_name="환각 위험 검증",
                passed=False,
                risk_level="high",
                message="Evidence 없이 수치 정보 포함 — 출처 불명 수치",
                details={"numbers_in_answer": answer_numbers[:5]},
            )
        return CheckResult(
            check_id="V007",
            check_name="환각 위험 검증",
            passed=True,
            risk_level="low",
            message="Evidence 기반 답변 확인",
        )

    # ─────────────────────────────────────────────────────────
    # V008 — 개인정보/민감정보 검증 (CRITICAL)
    # ─────────────────────────────────────────────────────────
    def _check_pii(self, answer: str) -> CheckResult:
        """
        답변에 주민번호·계좌번호·전화번호·이메일 패턴이 있으면 critical 실패.

        실패 시 run_all()에서 _apply_pii_masking()이 자동 적용된다.
        """
        found: list[str] = []
        for pattern, label in _PII_PATTERNS:
            if pattern.search(answer):
                found.append(label)

        if found:
            return CheckResult(
                check_id="V008",
                check_name="개인정보/민감정보 검증",
                passed=False,
                risk_level="critical",
                message=f"PII 패턴 감지: {found}",
                action_taken=f"마스킹 대상: {found}",
                details={"detected_pii_types": found},
            )
        return CheckResult(
            check_id="V008",
            check_name="개인정보/민감정보 검증",
            passed=True,
            risk_level="low",
            message="PII 패턴 미감지",
        )

    # ─────────────────────────────────────────────────────────
    # V009 — 답변 가능 범위 검증 (CRITICAL)
    # ─────────────────────────────────────────────────────────
    def _check_scope(self, answer: str, intent: str) -> CheckResult:
        """
        실제 대출 승인·계좌이체 등 AI 업무 범위 초과 키워드 감지 시 critical 실패.
        """
        matched = [kw for kw in _FORBIDDEN_SCOPE_KEYWORDS if kw in answer]
        if matched:
            return CheckResult(
                check_id="V009",
                check_name="답변 가능 범위 검증",
                passed=False,
                risk_level="critical",
                message=f"업무 범위 초과 표현 감지: {matched}",
                action_taken="해당 표현 제거 후 '영업점/앱 이용 안내'로 대체 권장",
                details={"forbidden_keywords": matched},
            )
        return CheckResult(
            check_id="V009",
            check_name="답변 가능 범위 검증",
            passed=True,
            risk_level="low",
            message="업무 범위 내 답변 확인",
        )

    # ─────────────────────────────────────────────────────────
    # V010 — 면책 안내 필요 검증
    # ─────────────────────────────────────────────────────────
    def _check_disclaimer_required(self, intent: str) -> CheckResult:
        """
        금융 상품 관련 의도(INQUIRY/COMPARISON/RECOMMENDATION/APPLICATION)이면
        면책 문구 삽입이 필요하다.
        passed=False → run_all()에서 면책 문구 자동 삽입.
        """
        intent_upper = (intent or "OTHER").upper()
        if intent_upper in _DISCLAIMER_INTENTS:
            return CheckResult(
                check_id="V010",
                check_name="면책 안내 필요 검증",
                passed=False,
                risk_level="high",
                message=f"금융 상담 의도({intent_upper}) — 면책 문구 삽입 필요",
                action_taken="면책 안내 문구 답변 말미 자동 삽입",
            )
        return CheckResult(
            check_id="V010",
            check_name="면책 안내 필요 검증",
            passed=True,
            risk_level="low",
            message="면책 문구 불필요한 의도",
        )

    # ─────────────────────────────────────────────────────────
    # 내부 유틸리티
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _apply_pii_masking(text: str) -> str:
        """PII 패턴을 마스킹 문자열로 치환한다."""
        for pattern, replacement in _PII_MASK_PATTERNS:
            text = pattern.sub(replacement, text)
        return text
