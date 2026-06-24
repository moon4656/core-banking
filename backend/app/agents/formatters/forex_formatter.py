"""forex_formatter.py — 외화 거래(환율·환전·송금·외화예금) API 응답 포맷터."""

from __future__ import annotations

from app.agents.formatters.base import AbstractFormatter
from app.schemas.ai_gateway import StepResult


class ForexFormatter(AbstractFormatter):
    supported_apis = [
        "MOCK_EXCHANGE_RATE_LOOKUP",
        "MOCK_CURRENCY_EXCHANGE_CALC",
        "MOCK_FOREIGN_REMITTANCE",
        "MOCK_FOREIGN_DEPOSIT_RATE",
    ]

    def format_single(self, result: StepResult, message: str = "") -> str:
        d = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_EXCHANGE_RATE_LOOKUP":
            return _fmt_exchange_rate(d)
        if api == "MOCK_CURRENCY_EXCHANGE_CALC":
            return _fmt_exchange_calc(d)
        if api == "MOCK_FOREIGN_REMITTANCE":
            return _fmt_remittance(d)
        if api == "MOCK_FOREIGN_DEPOSIT_RATE":
            return _fmt_deposit_rate(d)
        return ""

    def format_summary(self, result: StepResult) -> list[str]:
        data = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_EXCHANGE_RATE_LOOKUP":
            lines = ["■ 환율"]
            for er in data.get("rates", [])[:5]:
                change = er.get("change", 0)
                arrow = "▲" if change > 0 else ("▽" if change < 0 else "─")
                cur = er.get("currency", "")
                lines.append(
                    f"  · {cur} ({er.get('name','')}): "
                    f"기준 {er.get('standard','')}원  살때 {er.get('sell','')}원  팔때 {er.get('buy','')}원  {arrow}{abs(change)}원"
                )
            return lines

        if api == "MOCK_CURRENCY_EXCHANGE_CALC":
            from_c = data.get("from_currency", "")
            to_c = data.get("to_currency", "")
            fx_c = to_c if from_c == "KRW" else from_c
            from_amt = data.get("from_amount", 0)
            rate_app = data.get("rate_applied", 0)
            fee = data.get("fee_krw", 0)
            buy_r = data.get("buy_rate", "")
            sell_r = data.get("sell_rate", "")
            is_reverse = data.get("is_reverse_calc", False)
            lines = ["■ 환전 계산"]
            if is_reverse:
                to_amt = data.get("to_amount", 0)
                lines.append(f"  · 목표: {to_amt:,} {to_c}")
                lines.append(f"  · 적용 환율: {rate_app}원/{fx_c}")
                lines.append(f"  · 필요 원화: {from_amt:,.0f} KRW")
            else:
                if from_c == "KRW":
                    gross_str = f"{round(from_amt / rate_app, 4):,} {to_c}" if rate_app else ""
                else:
                    gross_str = f"{round(from_amt * rate_app, 0):,.0f}원"
                lines.append(f"  · 환전 신청금액: {from_amt:,} {from_c}")
                if buy_r and sell_r:
                    lines.append(f"  · 살때 {sell_r}원/{fx_c}  팔때 {buy_r}원/{fx_c}")
                lines.append(f"  · 적용 환율: {rate_app}원/{fx_c}")
                if gross_str:
                    lines.append(f"  · 환전 환산액: {gross_str}  ({from_amt:,} {from_c} × {rate_app}원)")
                lines.append(f"  · 수수료 차감: −{fee:,}원")
                lines.append(f"  · 수령 금액: {data.get('to_amount','')} {to_c}")
            return lines

        if api == "MOCK_FOREIGN_REMITTANCE":
            daily = data.get("daily_limit_usd", "")
            lines = ["■ 해외송금"]
            if daily:
                lines.append(f"  · 1일 송금 한도: ${daily:,}")
            for m in data.get("methods", [])[:2]:
                lines.append(f"  · {m.get('method','')}: {m.get('processing_time','')}")
            return lines

        if api == "MOCK_FOREIGN_DEPOSIT_RATE":
            lines = ["■ 외화예금 금리"]
            for dr in data.get("deposit_rates", [])[:4]:
                lines.append(
                    f"  · {dr.get('currency','')} ({dr.get('name','')}): "
                    f"정기12개월 {dr.get('time_deposit_12m','')}%"
                )
            return lines

        return [f"■ {api}"]


# ── 내부 포맷 함수 ────────────────────────────────────────────────────


def _fmt_exchange_rate(d: dict) -> str:
    rates_list: list[dict] = d.get("rates", [])
    timestamp: str = d.get("timestamp", "")[:10]
    if not rates_list:
        return "환율 정보를 조회할 수 없었습니다."
    title = f"■ 주요 환율 ({timestamp} 기준)" if timestamp else "■ 주요 환율"
    lines = [title]
    for r in rates_list:
        change = r.get("change", 0)
        arrow = "▲" if change > 0 else ("▽" if change < 0 else "─")
        cur = r.get("currency", "")
        lines.append(
            f"  · {cur} ({r.get('name','')}): "
            f"기준 {r.get('standard','')}원  살때 {r.get('sell','')}원  팔때 {r.get('buy','')}원  {arrow}{abs(change)}원"
        )
    note = d.get("note", "")
    if note:
        lines.append(f"\n  ※ {note}")
    return "\n".join(lines)


def _fmt_exchange_calc(d: dict) -> str:
    from_c = d.get("from_currency", "KRW")
    to_c = d.get("to_currency", "")
    from_amt = d.get("from_amount", 0)
    to_amt = d.get("to_amount", 0)
    rate_app = d.get("rate_applied", 0)
    fee = d.get("fee_krw", 0)
    discount = d.get("discount_rate", 0)
    note = d.get("note", "")
    buy_rate = d.get("buy_rate")
    sell_rate = d.get("sell_rate")
    std_rate = d.get("standard_rate", 0)
    is_reverse = d.get("is_reverse_calc", False)
    fx_code = to_c if from_c == "KRW" else from_c

    lines = [f"■ 환전 계산 결과 ({from_c} → {to_c})"]
    if is_reverse:
        net_krw = round(to_amt * rate_app, 0)
        lines.append(f"  · 목표 수령 금액: {to_amt:,} {to_c}")
        lines.append(f"  · 기준 환율: {std_rate:,}원/{fx_code}")
        if buy_rate and sell_rate:
            lines.append(f"  · 살때(고객 외화 매입): {sell_rate:,}원/{fx_code}")
            lines.append(f"  · 팔때(고객 외화 매도): {buy_rate:,}원/{fx_code}")
        lines.append(f"  · 적용 환율: {rate_app:,}원/{fx_code}")
        lines.append(f"  · 환산 원화: {net_krw:,.0f}원  ({to_amt:,} {to_c} × {rate_app:,}원)")
        lines.append(f"  · 수수료 추가: +{fee:,}원 (우대율 {discount}% 적용)")
        lines.append(f"  · 필요 원화: {from_amt:,.0f} KRW")
    else:
        if from_c == "KRW":
            gross_amt = round(from_amt / rate_app, 4) if rate_app else 0
            gross_str = f"{gross_amt:,} {to_c}"
        else:
            gross_amt = round(from_amt * rate_app, 0)
            gross_str = f"{gross_amt:,.0f}원"
        lines.append(f"  · 환전 신청금액: {from_amt:,} {from_c}")
        lines.append(f"  · 기준 환율: {std_rate:,}원/{fx_code}")
        if buy_rate and sell_rate:
            lines.append(f"  · 살때(고객 외화 매입): {sell_rate:,}원/{fx_code}")
            lines.append(f"  · 팔때(고객 외화 매도): {buy_rate:,}원/{fx_code}")
        lines.append(f"  · 적용 환율: {rate_app:,}원/{fx_code}")
        lines.append(f"  · 환전 환산액: {gross_str}  ({from_amt:,} {from_c} × {rate_app:,}원)")
        lines.append(f"  · 수수료 차감: −{fee:,}원 (우대율 {discount}% 적용)")
        lines.append(f"  · 수령 금액: {to_amt:,} {to_c}")
    if note:
        lines.append(f"\n  ※ {note}")
    return "\n".join(lines)


def _fmt_remittance(d: dict) -> str:
    methods_list: list[dict] = d.get("methods", [])
    daily_limit = d.get("daily_limit_usd", 0)
    fee_est = d.get("fee_estimate_krw")
    caution = d.get("caution", "")
    dest = d.get("destination_country")
    lines = ["■ 해외송금 안내"]
    if dest:
        lines.append(f"  · 수취국: {dest.get('name','')} — {dest.get('notes','')}")
    lines.append(f"  · 1일 인터넷 송금 한도: ${daily_limit:,}")
    if fee_est:
        lines.append(f"  · 예상 수수료: {fee_est:,}원")
    for m in methods_list[:2]:
        lines.append(f"  · {m.get('method','')}: {m.get('processing_time','')}")
    if caution:
        lines.append(f"\n  ⚠ {caution}")
    return "\n".join(lines)


def _fmt_deposit_rate(d: dict) -> str:
    deposit_rates: list[dict] = d.get("deposit_rates", [])
    note = d.get("note", "")
    if not deposit_rates:
        return "외화예금 금리 정보를 조회할 수 없었습니다."
    lines = ["■ 외화예금 금리"]
    for r in deposit_rates:
        lines.append(
            f"  · {r.get('currency','')} ({r.get('name','')}) — "
            f"보통예금 {r.get('demand_rate','')}% / "
            f"정기 6개월 {r.get('time_deposit_6m','')}% / "
            f"정기 12개월 {r.get('time_deposit_12m','')}%"
        )
    if note:
        lines.append(f"\n  ※ {note}")
    return "\n".join(lines)
