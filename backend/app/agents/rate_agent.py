# rate_agent.py — 금리 및 우대금리 전담 Sub Agent
#
# [담당 Concept]
#   CONCEPT_INTEREST_RATE    : 상품별 기준금리, 최종금리 범위
#   CONCEPT_PREFERENTIAL_RATE: 우대금리 조건 및 할인폭
#
# [사용 Tool]
#   MOCK_RATE_LOOKUP    : 금리 목록 조회
#   MOCK_RATE_SIMULATION: 월 상환금 / 총 이자 계산 — 사용자 메시지에서 금액/금리/기간 추출

import re

from sqlalchemy.orm import Session

from app.agents.base_agent import AbstractAgent, AgentInput, AgentOutput


def _extract_credit_grade(message: str) -> int | None:
    """
    사용자 메시지에서 신용등급(1~10)을 추출한다.
    예: "3등급인데", "신용등급 5등급", "내 등급은 7등급" → int
    """
    m = re.search(r'(\d{1,2})\s*등급', message)
    if m:
        grade = int(m.group(1))
        if 1 <= grade <= 10:
            return grade
    return None


_INTENT_PATTERN_CACHE: dict[str, re.Pattern] = {}


def clear_intent_pattern_cache(intent: str | None = None) -> list[str]:
    """캐시를 비운다. intent 지정 시 해당 키만, None이면 전체 삭제. 삭제된 키 목록 반환."""
    if intent:
        removed = [intent] if _INTENT_PATTERN_CACHE.pop(intent, None) else []
    else:
        removed = list(_INTENT_PATTERN_CACHE.keys())
        _INTENT_PATTERN_CACHE.clear()
    return removed


def _build_intent_pattern(intent: str, db) -> re.Pattern:
    """DB의 intent_term_synonym에서 용어를 읽어 정규식 패턴을 빌드한다. 결과는 프로세스 내 캐시."""
    if intent in _INTENT_PATTERN_CACHE:
        return _INTENT_PATTERN_CACHE[intent]

    from app.models.knowledge_model import IntentTermSynonym
    rows = db.query(IntentTermSynonym.term).filter(
        IntentTermSynonym.intent == intent,
        IntentTermSynonym.is_active == True,
    ).all()

    if rows:
        terms = [re.escape(r.term) for r in rows]
        pattern = re.compile("|".join(terms))
    else:
        # DB에 데이터가 없으면 기본 패턴으로 fallback
        _FALLBACK = {
            "RATE_MIN": re.compile(r'최저|최소|가장\s*낮은|낮은'),
            "RATE_MAX": re.compile(r'최고|최대|가장\s*높은|높은'),
        }
        pattern = _FALLBACK.get(intent, re.compile(r'(?!x)x'))

    _INTENT_PATTERN_CACHE[intent] = pattern
    return pattern


def _has_min_rate_request(message: str, db=None) -> bool:
    if db is None:
        return bool(re.search(r'최저|최소|가장\s*낮은|낮은', message))
    return bool(_build_intent_pattern("RATE_MIN", db).search(message))


def _has_max_rate_request(message: str, db=None) -> bool:
    if db is None:
        return bool(re.search(r'최고|최대|가장\s*높은|높은', message))
    return bool(_build_intent_pattern("RATE_MAX", db).search(message))


_PRODUCT_KEYWORDS = [
    # 긴(구체적) 키워드 우선 — "직장인"이 "중금리 사잇돌"보다 먼저 매칭되는 것을 방지
    "직장인 신용대출",
    "중금리 사잇돌2",   # 숫자 포함된 구체적 상품명 우선
    "중금리 사잇돌",
    "사잇돌",
    "주택담보대출",
    "주택담보",
    "전세자금",
    "마이너스통장",
    "자동차담보",
    "프리랜서",
    "자영업자",
    "직장인",   # 단독 "직장인"은 직업 설명일 수 있어 마지막 검사
]


def _extract_product_name(message: str) -> str | None:
    """사용자 메시지에서 대출 상품명 키워드를 추출한다. 구체적(긴) 키워드 우선."""
    for keyword in _PRODUCT_KEYWORDS:
        if keyword in message:
            return keyword
    return None


def _extract_simulation_params(message: str) -> dict:
    """
    사용자 메시지에서 MOCK_RATE_SIMULATION 파라미터를 추출한다.

    지원 패턴:
      금액 : "1000만원", "1억", "5천만원", "1억 5천만원"
      금리 : "5.5%", "금리 5.5", "연 5.5"
      기간 : "3년", "36개월"
      거치 : "3개월 거치", "3개월 이자" → grace_months=3
             "3개월 거치 12개월" → grace=3, repay=12, term=15
      방식 : "원금균등", "만기일시상환", 거치 있으면 "거치식원금균등" 또는 "거치식균등분할"
    추출 실패 시 빈 dict를 반환해 Mock API 기본값을 사용한다.
    """
    params: dict = {}

    # ── 금액 ────────────────────────────────────────────────────
    m_eok_man = re.search(r'(\d+(?:\.\d+)?)\s*억\s*(\d+)\s*천?\s*만원?', message)
    m_eok     = re.search(r'(\d+(?:\.\d+)?)\s*억원?', message)
    m_chun    = re.search(r'(\d+(?:\.\d+)?)\s*천\s*만원?', message)
    m_man     = re.search(r'(\d+(?:\.\d+)?)\s*만원?', message)

    if m_eok_man:
        params["principal"] = int(
            float(m_eok_man.group(1)) * 100_000_000
            + int(m_eok_man.group(2)) * 10_000_000
        )
    elif m_eok:
        params["principal"] = int(float(m_eok.group(1)) * 100_000_000)
    elif m_chun:
        params["principal"] = int(float(m_chun.group(1)) * 10_000_000)
    elif m_man:
        params["principal"] = int(float(m_man.group(1)) * 10_000)

    # ── 금리 ────────────────────────────────────────────────────
    m_rate = (
        re.search(r'(?:금리|연\s*이율?|연)\s*(\d+(?:\.\d+)?)\s*%?', message)
        or re.search(r'(\d+(?:\.\d+)?)\s*%', message)
    )
    if m_rate:
        params["annual_rate"] = float(m_rate.group(1))

    # ── 거치 기간 ────────────────────────────────────────────────
    # "3개월 거치 12개월" 패턴: 거치=3, 상환=12, 합계=15
    m_grace_repay = re.search(r'(\d+)\s*개월\s*(?:이자|거치)\s*(\d+)\s*개월', message)
    m_grace_only  = re.search(r'(\d+)\s*개월\s*(?:이자|거치)', message)

    if m_grace_repay:
        grace = int(m_grace_repay.group(1))
        repay = int(m_grace_repay.group(2))
        params["grace_months"] = grace
        params["term_months"]  = grace + repay   # 총 기간 = 거치 + 상환
    elif m_grace_only:
        grace = int(m_grace_only.group(1))
        params["grace_months"] = grace
        # 상환 기간은 아래 일반 기간 파싱으로 추가 처리

    # ── 기간 (거치+상환 복합이 아닌 경우) ──────────────────────────
    if "term_months" not in params:
        m_year  = re.search(r'(\d+)\s*년', message)
        # 거치 기간에 이미 쓰인 숫자를 제외하고 독립적인 개월 수를 찾는다.
        # 거치 패턴이 아닌 개월 숫자 중 가장 큰 값을 상환 기간으로 사용
        all_months = [int(m) for m in re.findall(r'(\d+)\s*개월', message)]
        grace_val  = params.get("grace_months", 0)

        if m_year:
            params["term_months"] = int(m_year.group(1)) * 12
        elif all_months:
            # 거치 개월을 제외한 나머지 개월 중 가장 큰 값을 상환 기간으로 사용
            non_grace = [m for m in all_months if m != grace_val] if grace_val else all_months
            repay = max(non_grace) if non_grace else (all_months[0] if all_months else None)
            if repay:
                params["term_months"] = grace_val + repay if grace_val else repay

    # ── 상환 방식 ────────────────────────────────────────────────
    has_grace = params.get("grace_months", 0) > 0
    if "만기일시" in message:
        params["method"] = "만기일시상환"
    elif "원금균등" in message and has_grace:
        params["method"] = "거치식원금균등"
    elif "원금균등" in message:
        params["method"] = "원금균등"
    elif has_grace:
        params["method"] = "거치식균등분할"

    return params


class RateAgent(AbstractAgent):
    """금리 및 상환 시뮬레이션 정보를 조회하는 Sub Agent."""

    @property
    def agent_id(self) -> str:
        return "RATE_AGENT"

    async def run(self, db: Session, input: AgentInput) -> AgentOutput:
        from app.tools.tool_gateway import invoke_tool
        from app.trace.trace_service import Timer

        sim_params = _extract_simulation_params(input.message)
        credit_grade = _extract_credit_grade(input.message)

        # 시뮬레이션 요청인데 금리가 메시지에 명시되지 않은 경우,
        # personalized rate 를 먼저 조회해 신용등급에 맞는 금리를 자동 주입한다.
        # (최저/최고 명시 여부와 무관하게 항상 실행)
        wants_min = _has_min_rate_request(input.message, db)
        wants_max = _has_max_rate_request(input.message, db)
        sim_requested = "MOCK_RATE_SIMULATION" in input.api_ids
        if sim_requested and "annual_rate" not in sim_params:
            grade = credit_grade or 5
            personalized = await invoke_tool(
                db, "MOCK_PERSONALIZED_RATE_LOOKUP", params={"credit_grade": grade}
            )
            if personalized.status == "success" and personalized.data:
                rates = personalized.data.get("rates", [])
                product_keyword = _extract_product_name(input.message)
                matched = (
                    next((r for r in rates if product_keyword and product_keyword in r["product_name"]), None)
                    or (rates[0] if rates else None)
                )
                if matched:
                    # 최저/최고 명시 없으면 min_rate 사용 (고객에게 유리한 기준)
                    sim_params["annual_rate"] = matched["max_rate"] if wants_max else matched["min_rate"]

        api_results: list[dict] = []
        for api_id in input.api_ids:
            if api_id == "MOCK_RATE_SIMULATION":
                params = sim_params
            elif api_id == "MOCK_PERSONALIZED_RATE_LOOKUP":
                # 신용등급이 메시지에 있으면 해당 등급으로, 없으면 기본값 5등급
                params = {"credit_grade": credit_grade} if credit_grade else {"credit_grade": 5}
            else:
                params = {}
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
            metadata={
                "processed_apis":  len(api_results),
                "sim_params_used": sim_params,
                "is_comparison":   input.intent.get("intent") == "COMPARISON",
            },
        )
