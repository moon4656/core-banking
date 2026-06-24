"""registry.py — 포맷터 등록 및 공개 dispatch 함수."""

from __future__ import annotations

from app.agents.formatters.base import AbstractFormatter
from app.agents.formatters.forex_formatter import ForexFormatter
from app.agents.formatters.loan_formatter import LoanFormatter
from app.agents.formatters.notification_formatter import NotificationFormatter
from app.agents.formatters.policy_formatter import PolicyFormatter
from app.schemas.ai_gateway import StepResult

_DISCLAIMER = (
    "\n\n※ 본 안내는 참고 목적이며, "
    "실제 금융 상품 조건은 영업점 또는 공식 앱에서 반드시 확인하시기 바랍니다."
)

# API ID → formatter 인스턴스 매핑
_REGISTRY: dict[str, AbstractFormatter] = {}


def _register(formatter: AbstractFormatter) -> None:
    for api_id in formatter.supported_apis:
        _REGISTRY[api_id] = formatter


_register(ForexFormatter())
_register(LoanFormatter())
_register(PolicyFormatter())
_register(NotificationFormatter())


def format_single(result: StepResult, message: str = "") -> str:
    """단일 결과 상세 포맷. 포맷터가 없으면 빈 문자열 반환."""
    formatter = _REGISTRY.get(result.api_id)
    if formatter:
        return formatter.format_single(result, message)
    return ""


def format_multi(results: list[StepResult]) -> str:
    """다중 결과 요약 포맷 (LLM fallback용). 모든 성공 결과를 섹션으로 결합."""
    if not results:
        return "요청하신 정보를 조회할 수 없었습니다. 다시 시도해 주세요."

    success = [r for r in results if r.status == "success" and r.data]
    errors = [r for r in results if r.status != "success"]
    sections: list[str] = []

    for r in success:
        data = r.data
        if not isinstance(data, dict):
            sections.append(f"■ {r.api_id}: 데이터 확인 완료")
            continue

        formatter = _REGISTRY.get(r.api_id)
        if formatter:
            lines = formatter.format_summary(r)
        else:
            # 등록되지 않은 API — 기본 key:value 3개
            lines = [f"■ {r.api_id}"]
            for k, v in list(data.items())[:3]:
                if v and not isinstance(v, (list, dict)):
                    lines.append(f"  · {k}: {v}")

        if len(lines) == 1:
            lines.append("  · 데이터 확인 완료")
        sections.append("\n".join(lines))

    if errors:
        _LABELS = {
            "MOCK_PRODUCT_LOOKUP": "대출 상품", "MOCK_RATE_LOOKUP": "금리",
            "MOCK_POLICY_LOOKUP": "정책/약관", "MOCK_DOCUMENT_SEARCH": "필요서류",
            "MOCK_RATE_SIMULATION": "금리 시뮬레이션", "MOCK_ELIGIBILITY_CHECK": "자격 조건",
            "MOCK_COUNSELING_HISTORY": "상담 이력", "MOCK_EXCHANGE_RATE_LOOKUP": "환율",
            "MOCK_CURRENCY_EXCHANGE_CALC": "환전 계산", "MOCK_FOREIGN_REMITTANCE": "해외송금",
            "MOCK_FOREIGN_DEPOSIT_RATE": "외화예금 금리", "MOCK_NOTIFICATION_RULES": "알림 규칙",
            "MOCK_NOTIFICATION_SEND": "알림 발송",
        }
        failed = [_LABELS.get(r.api_id, r.api_id) for r in errors]
        sections.append(f"⚠ 조회 실패: {', '.join(failed)}")

    if not sections:
        return "조회를 완료했으나 반환된 데이터가 없습니다."

    return "\n\n".join(sections) + _DISCLAIMER
