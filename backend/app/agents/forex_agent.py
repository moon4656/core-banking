# forex_agent.py — 외화 거래 전담 Sub Agent
#
# [담당 Concept]
#   CONCEPT_EXCHANGE_RATE   : 환율 조회 및 변동 현황
#   CONCEPT_CURRENCY_EXCHANGE: 외화 환전 계산 (원화 ↔ 외화)
#   CONCEPT_FOREIGN_REMITTANCE: 해외송금 한도·수수료·방법 안내
#   CONCEPT_FOREIGN_DEPOSIT : 외화예금 금리
#
# [사용 Tool]
#   MOCK_EXCHANGE_RATE_LOOKUP : 환율 조회
#   MOCK_CURRENCY_EXCHANGE_CALC: 환전 계산 (금액 파라미터 추출)
#   MOCK_FOREIGN_REMITTANCE   : 해외송금 안내
#   MOCK_FOREIGN_DEPOSIT_RATE : 외화예금 금리

import re

from sqlalchemy.orm import Session

from app.agents.base_agent import AbstractAgent, AgentInput, AgentOutput


def _extract_forex_params(api_id: str, message: str) -> dict:
    """사용자 메시지에서 외화 거래 파라미터를 추출한다."""
    params: dict = {}

    if api_id == "MOCK_EXCHANGE_RATE_LOOKUP":
        currency_map = {
            "달러": "USD", "USD": "USD",
            "엔화": "JPY", "엔": "JPY", "JPY": "JPY",
            "유로": "EUR", "EUR": "EUR",
            "위안": "CNY", "CNY": "CNY",
            "파운드": "GBP", "GBP": "GBP",
        }
        for keyword, code in currency_map.items():
            if keyword in message:
                params["currency"] = code
                break

    elif api_id == "MOCK_CURRENCY_EXCHANGE_CALC":
        foreign_currency_map = {
            "달러": "USD", "USD": "USD", "$": "USD",
            "엔화": "JPY", "엔": "JPY", "JPY": "JPY",
            "유로": "EUR", "EUR": "EUR",
            "위안": "CNY", "CNY": "CNY",
        }

        # 원화 단위 금액: 1억, 100만, 50000원
        m_eok = re.search(r'(\d+(?:\.\d+)?)\s*억', message)
        m_man = re.search(r'(\d+(?:\.\d+)?)\s*만', message)
        m_won = re.search(r'(\d[\d,]*)\s*원(?!/)', message)  # '1355.5원/USD' 같은 환율 표기 제외

        # 외화 단위 금액: "100달러", "50 USD", "200엔"
        foreign_pattern = r'(\d+(?:\.\d+)?)\s*(달러|USD|\$|엔화|엔|JPY|유로|EUR|위안|CNY)'
        m_foreign = re.search(foreign_pattern, message, re.IGNORECASE)

        # 역산 방향 키워드: "달러로 환전", "달러로 바꿔" → KRW→외화(목표 금액)
        target_dir_pattern = r'(달러|USD|엔화|엔|JPY|유로|EUR|위안|CNY)로\s*(?:환전|바꿔|사고|살)'
        m_target_dir = re.search(target_dir_pattern, message, re.IGNORECASE)

        if m_eok or m_man or m_won:
            # KRW → 외화 방향 (원화 금액 명시)
            if m_eok:
                params["amount"] = int(float(m_eok.group(1)) * 100_000_000)
            elif m_man:
                params["amount"] = int(float(m_man.group(1)) * 10_000)
            else:
                params["amount"] = int(m_won.group(1).replace(",", ""))
            params["from_currency"] = "KRW"
            for keyword, code in foreign_currency_map.items():
                if keyword in message:
                    params["to_currency"] = code
                    break
        elif m_target_dir and m_foreign:
            # 역산: "달러로 환전해줘 1000달러" → 1000 USD 받으려면 원화 얼마?
            dir_ccy  = foreign_currency_map.get(m_target_dir.group(1), "USD")
            amt_ccy  = foreign_currency_map.get(m_foreign.group(2), "USD")
            if dir_ccy == amt_ccy:
                # 방향 통화와 금액 통화가 일치 → 역산 KRW→외화
                params["target_amount"] = float(m_foreign.group(1))
                params["from_currency"] = "KRW"
                params["to_currency"]   = dir_ccy
            else:
                # 통화 불일치 → 일반 외화→KRW 처리
                params["amount"]        = float(m_foreign.group(1))
                params["from_currency"] = amt_ccy
                params["to_currency"]   = "KRW"
        elif m_foreign:
            # 외화 → KRW 방향 (예: "100달러 환전해줘")
            foreign_word = m_foreign.group(2)
            params["amount"] = float(m_foreign.group(1))
            params["from_currency"] = foreign_currency_map.get(foreign_word, "USD")
            params["to_currency"] = "KRW"
        else:
            # 금액 없음 → 통화만 설정, 기본 방향 KRW → 외화
            for keyword, code in foreign_currency_map.items():
                if keyword in message:
                    params["to_currency"] = code
                    params["from_currency"] = "KRW"
                    break

    elif api_id == "MOCK_FOREIGN_REMITTANCE":
        country_map = {
            "미국": "US", "USA": "US",
            "일본": "JP", "Japan": "JP",
            "중국": "CN", "China": "CN",
            "베트남": "VN",
        }
        for keyword, code in country_map.items():
            if keyword in message:
                params["destination_country"] = code
                break

        m_amount = re.search(r'(\d+(?:\.\d+)?)\s*(?:달러|USD|\$)', message)
        if m_amount:
            params["amount"] = float(m_amount.group(1))

    elif api_id == "MOCK_FOREIGN_DEPOSIT_RATE":
        currency_map = {
            "달러": "USD", "USD": "USD",
            "엔화": "JPY", "엔": "JPY", "JPY": "JPY",
            "유로": "EUR", "EUR": "EUR",
        }
        for keyword, code in currency_map.items():
            if keyword in message:
                params["currency"] = code
                break

    return params


class ForexAgent(AbstractAgent):
    """외화 거래(환율·환전·송금·외화예금) 정보를 조회하는 Sub Agent."""

    @property
    def agent_id(self) -> str:
        return "FOREX_AGENT"

    async def run(self, db: Session, input: AgentInput) -> AgentOutput:
        from app.tools.tool_gateway import invoke_tool
        from app.trace.trace_service import Timer

        api_results: list[dict] = []
        for api_id in input.api_ids:
            params = _extract_forex_params(api_id, input.message)
            t = Timer()
            result = await invoke_tool(db, api_id, params=params)
            latency_ms = result.latency_ms if result.latency_ms is not None else t.elapsed_ms()
            api_results.append({
                "api_id":        api_id,
                "status":        result.status,
                "data":          result.data,
                "error":         result.error,
                "latency_ms":    latency_ms,
                "output_masked": result.output_masked,
            })

        success_count = sum(1 for r in api_results if r["status"] == "success")
        confidence = success_count / len(api_results) if api_results else 0.0

        return AgentOutput(
            agent_id=self.agent_id,
            api_results=api_results,
            confidence=confidence,
            metadata={"processed_apis": len(api_results)},
        )
