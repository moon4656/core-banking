# evidence_scorer.py — 근거(Evidence) 신뢰도 점수 실제 계산 엔진
#
# [신뢰도 점수가 필요한 이유 — 은행권 맥락]
#   AI 응답의 출처가 되는 데이터가 얼마나 믿을 만한지 수치화한다.
#   단순히 API 호출 성공/실패가 아니라 실제 데이터 품질을 평가한다.
#
# [세 가지 측정 축]
#
#   1. data_quality_score (0.0~1.0) — 데이터 완성도
#      - API 응답에 필수 필드가 모두 있는가?
#      - 반환된 데이터 항목 수가 충분한가?
#      - 중요 수치(금리, 금액 등)가 null이 아닌가?
#      가중치: 50% (데이터 자체의 신뢰성이 가장 중요)
#
#   2. intent_relevance_score (0.0~1.0) — 의도 관련도
#      - 이 API가 사용자의 질문 유형(INQUIRY/COMPARISON/APPLICATION/...)에 적합한가?
#      - 금리 비교 질문에 금리 데이터가 왔으면 높은 점수
#      - 금리 비교 질문에 영업점 데이터가 왔으면 낮은 점수
#      가중치: 40%
#
#   3. latency_bonus (0.5~1.0) — 응답 속도 보너스
#      - 2초 이내: 1.0 (신선한 데이터)
#      - 2~5초: 0.8
#      - 5초 초과: 0.5
#      가중치: 10% (중요도 낮지만 느린 API는 약간 페널티)
#
# [최종 confidence_score]
#   = 0.5 × data_quality + 0.4 × intent_relevance + 0.1 × latency_bonus
#
# [quality_flags 예시]
#   {
#     "has_required_fields": true,
#     "item_count": 3,
#     "has_null_critical_fields": false,
#     "schema_match": true
#   }

from dataclasses import dataclass, field


@dataclass
class EvidenceScore:
    """
    Evidence 하나에 대한 점수 계산 결과.

    confidence_score       : 최종 종합 신뢰도 (0.0 ~ 1.0)
    data_quality_score     : 데이터 완성도
    intent_relevance_score : 사용자 의도와의 관련도
    item_count             : 반환된 데이터 레코드 수
    quality_flags          : 세부 품질 체크 결과 dict
    """
    confidence_score:       float
    data_quality_score:     float
    intent_relevance_score: float
    item_count:             int
    quality_flags:          dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# API별 필수 필드 정의
#
# 각 API 응답에서 반드시 있어야 하는 필드를 정의한다.
# 목록 타입 API는 (list_key, 항목 내 필수 필드 목록) 형태.
# ─────────────────────────────────────────────────────────────
_REQUIRED_FIELDS: dict[str, dict] = {
    "MOCK_PRODUCT_LOOKUP": {
        "list_key": "products",
        # mock-api/main.py _PRODUCTS 실제 필드명 기준
        "required_item_fields": ["product_id", "name", "min_amount", "max_amount"],
        "critical_numeric_fields": ["min_amount", "max_amount"],
    },
    "MOCK_RATE_LOOKUP": {
        "list_key": "rates",
        # mock-api/main.py _RATES 실제 필드명: base_rate (annual_rate 아님)
        "required_item_fields": ["product_id", "base_rate", "rate_type"],
        "critical_numeric_fields": ["base_rate"],
    },
    "MOCK_POLICY_LOOKUP": {
        "list_key": "policies",
        "required_item_fields": ["policy_id", "policy_type", "detail"],
        "critical_numeric_fields": [],
    },
    "MOCK_DOCUMENT_SEARCH": {
        "list_key": "documents",
        # mock-api/main.py _DOCUMENTS 실제 필드명: doc_id, name (document_id/document_name 아님)
        "required_item_fields": ["doc_id", "name", "category"],
        "critical_numeric_fields": [],
    },
    "MOCK_RATE_SIMULATION": {
        "list_key": None,  # 단건 응답
        "required_item_fields": ["monthly_payment", "total_interest", "total_payment"],
        "critical_numeric_fields": ["monthly_payment", "total_interest"],
    },
    "MOCK_ELIGIBILITY_CHECK": {
        "list_key": None,
        "required_item_fields": ["eligible", "estimated_rate"],
        "critical_numeric_fields": [],
    },
    "MOCK_COUNSELING_HISTORY": {
        "list_key": "histories",
        "required_item_fields": ["history_id", "customer_id", "channel"],
        "critical_numeric_fields": [],
    },
    "MOCK_BRANCH_LOOKUP": {
        "list_key": "branches",
        "required_item_fields": ["branch_id", "name", "address"],
        "critical_numeric_fields": [],
    },
}

# 의도(intent) × api_id 관련도 점수표 (0.0 ~ 1.0)
# 1.0: 이 의도에서 이 API 데이터는 핵심
# 0.5: 보조적으로 유용
# 0.2: 해당 의도에서는 거의 필요 없음
_INTENT_RELEVANCE_TABLE: dict[str, dict[str, float]] = {
    "INQUIRY": {
        "MOCK_PRODUCT_LOOKUP":     0.8,
        "MOCK_RATE_LOOKUP":        1.0,
        "MOCK_POLICY_LOOKUP":      0.6,
        "MOCK_DOCUMENT_SEARCH":    0.5,
        "MOCK_RATE_SIMULATION":    0.4,
        "MOCK_ELIGIBILITY_CHECK":  0.4,
        "MOCK_COUNSELING_HISTORY": 0.3,
        "MOCK_BRANCH_LOOKUP":      0.3,
    },
    "COMPARISON": {
        "MOCK_PRODUCT_LOOKUP":     0.9,
        "MOCK_RATE_LOOKUP":        1.0,
        "MOCK_POLICY_LOOKUP":      0.5,
        "MOCK_DOCUMENT_SEARCH":    0.3,
        "MOCK_RATE_SIMULATION":    0.8,  # 비교 시 월납입금 계산도 중요
        "MOCK_ELIGIBILITY_CHECK":  0.4,
        "MOCK_COUNSELING_HISTORY": 0.2,
        "MOCK_BRANCH_LOOKUP":      0.1,
    },
    "RECOMMENDATION": {
        "MOCK_PRODUCT_LOOKUP":     1.0,
        "MOCK_RATE_LOOKUP":        0.9,
        "MOCK_POLICY_LOOKUP":      0.7,
        "MOCK_DOCUMENT_SEARCH":    0.4,
        "MOCK_RATE_SIMULATION":    0.6,
        "MOCK_ELIGIBILITY_CHECK":  0.9,  # 추천 시 자격 확인이 핵심
        "MOCK_COUNSELING_HISTORY": 0.5,
        "MOCK_BRANCH_LOOKUP":      0.2,
    },
    "APPLICATION": {
        "MOCK_PRODUCT_LOOKUP":     0.6,
        "MOCK_RATE_LOOKUP":        0.5,
        "MOCK_POLICY_LOOKUP":      0.9,  # 신청 절차=정책 정보가 핵심
        "MOCK_DOCUMENT_SEARCH":    1.0,  # 필요서류가 최우선
        "MOCK_RATE_SIMULATION":    0.3,
        "MOCK_ELIGIBILITY_CHECK":  1.0,  # 신청 자격도 최우선
        "MOCK_COUNSELING_HISTORY": 0.4,
        "MOCK_BRANCH_LOOKUP":      0.6,  # 방문 신청 안내
    },
    "OTHER": {
        "MOCK_PRODUCT_LOOKUP":     0.5,
        "MOCK_RATE_LOOKUP":        0.5,
        "MOCK_POLICY_LOOKUP":      0.5,
        "MOCK_DOCUMENT_SEARCH":    0.5,
        "MOCK_RATE_SIMULATION":    0.5,
        "MOCK_ELIGIBILITY_CHECK":  0.5,
        "MOCK_COUNSELING_HISTORY": 0.5,
        "MOCK_BRANCH_LOOKUP":      0.5,
    },
}


def score_evidence(
    api_id: str,
    data: dict | list | None,
    intent: str,
    response_latency_ms: int,
) -> EvidenceScore:
    """
    Evidence 하나의 신뢰도를 계산해 EvidenceScore로 반환한다.

    Args:
        api_id              : API 식별자 (예: "MOCK_RATE_LOOKUP")
        data                : API 응답 JSON (성공 시)
        intent              : 사용자 의도 (예: "INQUIRY")
        response_latency_ms : API 응답에 걸린 시간 (ms)

    Returns:
        EvidenceScore : 계산된 점수들
    """
    if data is None:
        # 데이터가 없으면 모두 0점
        return EvidenceScore(
            confidence_score=0.0,
            data_quality_score=0.0,
            intent_relevance_score=0.0,
            item_count=0,
            quality_flags={"error": "no_data"},
        )

    data_quality, item_count, flags = _score_data_quality(api_id, data)
    intent_relevance = _score_intent_relevance(api_id, intent)
    latency_bonus = _score_latency(response_latency_ms)

    confidence = round(
        0.5 * data_quality + 0.4 * intent_relevance + 0.1 * latency_bonus,
        4,
    )

    return EvidenceScore(
        confidence_score=confidence,
        data_quality_score=round(data_quality, 4),
        intent_relevance_score=round(intent_relevance, 4),
        item_count=item_count,
        quality_flags=flags,
    )


def _score_data_quality(
    api_id: str,
    data: dict | list,
) -> tuple[float, int, dict]:
    """
    API 응답 데이터의 완성도를 평가한다.

    반환: (data_quality_score, item_count, quality_flags)

    [평가 기준]
    1. 필수 필드 존재 여부 (최대 0.6점)
    2. 항목 수 보너스 (최대 0.4점): 1건=0.1, 3건=0.2, 5건 이상=0.4
    3. 필수 수치 필드가 null이면 -0.2 페널티

    API별 스펙(_REQUIRED_FIELDS)이 정의되지 않은 경우 기본 점수 0.7 반환.
    """
    spec = _REQUIRED_FIELDS.get(api_id)
    flags: dict = {}

    # 스펙 정의 없는 API: 기본 점수
    if spec is None:
        item_count = len(data) if isinstance(data, list) else 1
        return 0.7, item_count, {"spec_defined": False}

    # dict로 정규화 (list 응답은 {"data": [...]} 형태)
    data_dict: dict = data if isinstance(data, dict) else {"data": data}

    list_key = spec["list_key"]
    required_fields = spec["required_item_fields"]
    critical_numeric = spec["critical_numeric_fields"]

    # ── 단건 응답 (list_key=None) ────────────────────────────
    if list_key is None:
        item_count = 1
        present = [f for f in required_fields if f in data_dict and data_dict[f] is not None]
        coverage = len(present) / len(required_fields) if required_fields else 1.0
        flags["required_fields_coverage"] = round(coverage, 2)
        flags["present_fields"] = present

        # 필수 수치 필드 null 체크
        null_critical = [f for f in critical_numeric if data_dict.get(f) is None]
        flags["null_critical_fields"] = null_critical

        score = 0.6 * coverage + 0.2  # 단건이므로 항목 수 보너스 기본값 적용
        if null_critical:
            score -= 0.2
        return max(0.0, min(1.0, score)), item_count, flags

    # ── 목록 응답 ─────────────────────────────────────────────
    items: list = data_dict.get(list_key, [])
    item_count = len(items)
    flags["item_count"] = item_count

    if item_count == 0:
        flags["empty_list"] = True
        return 0.1, 0, flags

    # 첫 번째 항목(대표 샘플)으로 필드 완성도 측정
    sample = items[0] if isinstance(items[0], dict) else {}
    present = [f for f in required_fields if f in sample and sample[f] is not None]
    coverage = len(present) / len(required_fields) if required_fields else 1.0
    flags["required_fields_coverage"] = round(coverage, 2)

    # 필수 수치 null 체크 (샘플 기준)
    null_critical = [f for f in critical_numeric if sample.get(f) is None]
    flags["null_critical_fields"] = null_critical

    # 항목 수 보너스 (0.1 ~ 0.4)
    count_bonus = min(item_count / 10.0, 0.4)  # 항목 4개 이상이면 최대 0.4

    score = 0.6 * coverage + count_bonus
    if null_critical:
        score -= 0.2
    return max(0.0, min(1.0, score)), item_count, flags


def _score_intent_relevance(api_id: str, intent: str) -> float:
    """
    사용자 의도(intent)와 API의 관련도 점수를 반환한다 (0.0 ~ 1.0).
    등록되지 않은 intent는 OTHER 테이블을 사용한다.
    """
    intent_upper = (intent or "OTHER").upper()
    table = _INTENT_RELEVANCE_TABLE.get(intent_upper, _INTENT_RELEVANCE_TABLE["OTHER"])
    return table.get(api_id, 0.5)


def rank_evidence_by_slots(
    slots: list,
    evidence_results: list[dict],
) -> list:
    """
    수집된 Evidence를 Answer Slot별로 랭킹한다.

    Args:
        slots            : List[AnswerSlot] — _extract_answer_slots()가 반환한 슬롯 목록
        evidence_results : [{"api_id": ..., "evidence_id": ..., "confidence_score": ...}]
                           leader.py에서 Evidence 저장 시 수집한 경량 딕셔너리
    Returns:
        List[AnswerSlotRanking] — 슬롯별 랭킹 결과
    """
    from app.schemas.decision_trace import AnswerSlotRanking, EvidenceCandidate

    rankings = []
    for slot in slots:
        # 이 슬롯에 연결된 Tool의 Evidence 후보 수집
        candidates = [
            ev for ev in evidence_results
            if ev.get("api_id") in (slot.tools or [])
        ]

        # confidence_score 내림차순 정렬
        candidates.sort(key=lambda x: x.get("confidence_score", 0.0), reverse=True)

        candidate_items = [
            EvidenceCandidate(
                evidence_id=c.get("evidence_id"),
                api_id=c["api_id"],
                confidence_score=round(c.get("confidence_score", 0.0), 4),
                rank=i + 1,
            )
            for i, c in enumerate(candidates)
        ]

        best = candidate_items[0] if candidate_items else None
        rankings.append(
            AnswerSlotRanking(
                slot_name=slot.slot_name,
                label_ko=slot.label_ko,
                best_evidence=best,
                candidates=candidate_items,
                slot_filled=best is not None,
            )
        )

    return rankings


def _score_latency(latency_ms: int) -> float:
    """
    API 응답 속도에 따른 보너스 점수 (0.5 ~ 1.0).

    2초 이내: 1.0 (데이터 신선도 양호)
    2~5초:    0.8 (약간 느림)
    5초 초과: 0.5 (느린 API 페널티)
    """
    if latency_ms <= 2_000:
        return 1.0
    elif latency_ms <= 5_000:
        return 0.8
    return 0.5
