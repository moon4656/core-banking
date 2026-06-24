"""loan_formatter.py — 대출/금리 관련 API 응답 포맷터."""

from __future__ import annotations

from app.agents.formatters.base import AbstractFormatter
from app.schemas.ai_gateway import StepResult

_DISCLAIMER = "\n\n※ 본 안내는 참고 목적이며, 실제 금융 상품 조건은 영업점 또는 공식 앱에서 반드시 확인하시기 바랍니다."


class LoanFormatter(AbstractFormatter):
    supported_apis = [
        "MOCK_PRODUCT_LOOKUP",
        "MOCK_RATE_LOOKUP",
        "MOCK_RATE_SIMULATION",
        "MOCK_PERSONALIZED_RATE_LOOKUP",
        "MOCK_ELIGIBILITY_CHECK",
    ]

    def format_single(self, result: StepResult, message: str = "") -> str:
        d = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_RATE_SIMULATION":
            return _fmt_rate_simulation(d, message)
        if api == "MOCK_RATE_LOOKUP":
            return _fmt_rate_lookup(d, message)
        if api == "MOCK_ELIGIBILITY_CHECK":
            return _fmt_eligibility(d)
        if api == "MOCK_PERSONALIZED_RATE_LOOKUP":
            return _fmt_personalized_rate(d)
        if api == "MOCK_PRODUCT_LOOKUP":
            return _fmt_product_lookup(d)
        return ""

    def format_summary(self, result: StepResult) -> list[str]:
        data = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_RATE_LOOKUP":
            lines = ["■ 금리"]
            for rate in data.get("rates", [])[:5]:
                name = rate.get("product_name", "")
                lo = rate.get("min_final_rate", "")
                hi = rate.get("max_final_rate", "")
                max_pref = rate.get("max_preferential", 0)
                if name:
                    lines.append(f"  · {name}: {lo}% ~ {hi}%")
                    if max_pref:
                        lines.append(f"    (우대금리 최대 {max_pref}%p 할인 가능)")
            return lines

        if api == "MOCK_RATE_SIMULATION":
            lines = ["■ 금리 시뮬레이션"]
            example = data.get("example")
            if example:
                lines.append(f"  · {example}")
            monthly = data.get("monthly_payment")
            grace_monthly = data.get("grace_monthly_interest")
            first_repay = data.get("first_repay_payment")
            last_repay = data.get("last_repay_payment")
            total_interest = data.get("total_interest")
            if monthly:
                lines.append(f"  · 월 납입금: {monthly:,}원")
            elif grace_monthly is not None and first_repay is not None and last_repay is not None:
                lines.append(f"  · 거치 기간 월 이자: {grace_monthly:,}원")
                lines.append(f"  · 상환 구간: 첫달 {first_repay:,}원 / 마지막달 {last_repay:,}원")
            if total_interest:
                lines.append(f"  · 총 이자: {total_interest:,}원")
            return lines

        if api == "MOCK_PRODUCT_LOOKUP":
            lines = ["■ 대출 상품"]
            for prod in data.get("products", [])[:4]:
                name = prod.get("name", "")
                lo = prod.get("min_rate", "")
                hi = prod.get("max_rate", "")
                limit = prod.get("max_amount")
                if name:
                    rate_str = f" ({lo}%~{hi}%)" if lo and hi else ""
                    limit_str = f" / 한도 {limit:,}원" if limit else ""
                    lines.append(f"  · {name}{rate_str}{limit_str}")
            return lines

        if api == "MOCK_PERSONALIZED_RATE_LOOKUP":
            grade = data.get("credit_grade", "?")
            label = data.get("grade_label", "")
            lines = [f"■ 신용등급 {grade}등급({label}) 맞춤 금리"]
            for pr in data.get("rates", [])[:4]:
                lines.append(
                    f"  · {pr.get('product_name','')}: "
                    f"연 {pr.get('min_rate','')}% ~ {pr.get('max_rate','')}%"
                )
            return lines

        if api == "MOCK_ELIGIBILITY_CHECK":
            lines = ["■ 자격 조건"]
            recommendation = data.get("recommendation", "")
            if recommendation:
                lines.append(f"  · {recommendation}")
            for issue in data.get("issues", [])[:2]:
                lines.append(f"  · ⚠ {issue}")
            return lines

        return [f"■ {api}"]


# ── 내부 포맷 함수 ────────────────────────────────────────────────────


def _fmt_rate_simulation(d: dict, message: str) -> str:
    principal = d.get("principal", 0)
    rate = d.get("annual_rate", 0)
    term = d.get("term_months", 0)
    method = d.get("method", "")
    total = d.get("total_payment", 0)
    interest = d.get("total_interest", 0)

    from app.agents.rate_agent import _extract_product_name, _extract_credit_grade
    _product = _extract_product_name(message) if message else None
    _grade = _extract_credit_grade(message) if message else None
    _rate_source = ""
    if _product:
        _grade_label = f"{_grade}등급 기준" if _grade else "신용등급 5등급(기본) 기준"
        _rate_source = f" ({_product} / {_grade_label})"

    if method == "거치식균등분할":
        grace = d.get("grace_months", 0)
        grace_monthly = d.get("grace_monthly_interest", 0)
        repay = d.get("repay_months", 0)
        repay_monthly = d.get("repay_monthly_payment", 0)
        return (
            f"■ 금리 시뮬레이션 결과 (거치식 균등분할){_rate_source}\n"
            f"  · 대출원금: {principal:,}원 / 연 {rate}% / {term}개월\n"
            f"  · 거치 기간 {grace}개월: 월 이자 {grace_monthly:,}원\n"
            f"  · 균등분할 {repay}개월: 월 납입금 {repay_monthly:,}원\n"
            f"  · 총 이자: {interest:,}원\n"
            f"  · 총 상환금액: {total:,}원"
        )

    if method == "거치식원금균등상환":
        grace = d.get("grace_months", 0)
        grace_monthly = d.get("grace_monthly_interest", 0)
        repay = d.get("repay_months", 0)
        first_repay = d.get("first_repay_payment", 0)
        last_repay = d.get("last_repay_payment", 0)
        return (
            f"■ 금리 시뮬레이션 결과 (거치식 원금균등상환){_rate_source}\n"
            f"  · 대출원금: {principal:,}원 / 연 {rate}% / {term}개월\n"
            f"  · 거치 기간 {grace}개월: 월 이자 {grace_monthly:,}원\n"
            f"  · 원금균등 {repay}개월: 첫달 {first_repay:,}원 / 마지막달 {last_repay:,}원\n"
            f"  · 총 이자: {interest:,}원\n"
            f"  · 총 상환금액: {total:,}원"
        )

    monthly = d.get("monthly_payment", 0)
    return (
        f"■ 금리 시뮬레이션 결과{_rate_source}\n"
        f"  · 대출원금: {principal:,}원 / 연 {rate}% / {term}개월 ({method})\n"
        f"  · 월 납입금: {monthly:,}원\n"
        f"  · 총 이자: {interest:,}원\n"
        f"  · 총 상환금액: {total:,}원"
    )


def _fmt_rate_lookup(d: dict, message: str) -> str:
    rates = d.get("rates", [])
    if not rates:
        return "금리 정보를 조회할 수 없었습니다."
    filtered = [
        r for r in rates
        if any(kw in r.get("product_name", "") for kw in message.split() if len(kw) >= 3)
    ]
    display = filtered if filtered else rates
    title = "■ 금리 비교" if len(display) > 1 else "■ 금리 안내"
    lines = [title]
    for r in display:
        pref = r.get("max_preferential", 0)
        lines.append(
            f"  · {r.get('product_name','')}: "
            f"{r.get('min_final_rate','')}% ~ {r.get('max_final_rate','')}%"
            + (f"  (우대금리 최대 {pref}%p 할인)" if pref else "")
        )
    return "\n".join(lines)


def _fmt_eligibility(d: dict) -> str:
    eligible = d.get("eligible", False)
    product = d.get("product_name", "")
    rec = d.get("recommendation", "")
    est_rate = d.get("estimated_rate")
    issues: list = d.get("issues", [])
    warnings: list = d.get("warnings", [])
    status = "신청 가능합니다." if eligible else "신청 조건을 충족하지 않습니다."
    header = f"■ 자격 조건 ({product})" if product else "■ 자격 조건"
    main_msg = rec if rec else status
    lines = [header, f"  · {main_msg}"]
    if est_rate:
        lines.append(f"  · 예상 적용 금리: 연 {est_rate}%")
    for w in warnings:
        lines.append(f"  ⚠ {w}")
    for issue in issues:
        lines.append(f"  ✗ {issue}")
    return "\n".join(lines)


def _fmt_personalized_rate(d: dict) -> str:
    grade = d.get("credit_grade", "?")
    grade_label = d.get("grade_label", "")
    rates_list: list[dict] = d.get("rates", [])
    if not rates_list:
        return f"신용등급 {grade}등급에 해당하는 대출 상품 금리 정보를 찾을 수 없습니다."
    lines = [f"■ 신용등급 {grade}등급({grade_label}) 맞춤 금리"]
    for r in rates_list:
        lines.append(f"  · {r.get('product_name','')}: 연 {r.get('min_rate','')}% ~ {r.get('max_rate','')}%")
    note = d.get("note", "")
    if note:
        lines.append(f"\n  ※ {note}")
    return "\n".join(lines)


def _fmt_product_lookup(d: dict) -> str:
    products: list[dict] = d.get("products", [])
    if not products:
        return "상품 정보를 조회할 수 없었습니다."
    lines = ["■ 대출 상품 안내"]
    for p in products:
        limit: int = p.get("max_amount", 0)
        if limit >= 100_000_000:
            eok = limit // 100_000_000
            rem = (limit % 100_000_000) // 10_000_000
            limit_str = f"{eok}억" + (f" {rem}천만" if rem else "")
        elif limit >= 10_000_000:
            limit_str = f"{limit // 10_000_000}천만"
        else:
            limit_str = f"{limit // 10_000}만"
        lines.append(
            f"  · {p.get('name','')}"
            f" | 금리 {p.get('min_rate','')}% ~ {p.get('max_rate','')}%"
            f" | 한도 {limit_str}원"
        )
    return "\n".join(lines)
