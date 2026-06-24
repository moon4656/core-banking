# concept_constants.py — Concept 분류 / Decision Rule / Answer Slot 상수
#
# Phase 1에서 정의, Phase 2(Concept 분류 로직)에서 참조한다.
# leader.py에 하드코딩하지 않고 여기서 일괄 관리한다.

from app.schemas.decision_trace import ConceptCategory

# ─────────────────────────────────────────────────────────────
# Concept별 카테고리 분류 threshold
#
# confidence >= core_threshold    → Core
# confidence >= support_threshold → Supporting
# confidence >= ref_threshold     → Reference
# confidence <  ref_threshold     → 제외
# ─────────────────────────────────────────────────────────────
THRESHOLD_CORE       = 0.80
THRESHOLD_SUPPORTING = 0.65
THRESHOLD_REFERENCE  = 0.60

# Concept별 임계값 오버라이드 (기본값과 다른 경우만 명시)
CONCEPT_THRESHOLD_OVERRIDES: dict[str, dict[str, float]] = {
    # 현재 MVP에서는 모든 Concept가 동일 threshold를 사용한다.
    # 향후 개별 조정이 필요하면 여기에 추가한다.
    # 예: "CONCEPT_CUSTOMER": {"core": 0.85, "supporting": 0.70, "reference": 0.60},
}


def get_threshold(concept_id: str) -> dict[str, float]:
    """concept_id에 해당하는 threshold 딕셔너리를 반환한다."""
    override = CONCEPT_THRESHOLD_OVERRIDES.get(concept_id)
    if override:
        return override
    return {
        "core":       THRESHOLD_CORE,
        "supporting": THRESHOLD_SUPPORTING,
        "reference":  THRESHOLD_REFERENCE,
    }


def classify_concept(concept_id: str, confidence: float) -> ConceptCategory | None:
    """
    confidence 값을 threshold와 비교해 ConceptCategory를 반환한다.
    모든 threshold 미달이면 None(제외)을 반환한다.
    """
    t = get_threshold(concept_id)
    if confidence >= t["core"]:
        return ConceptCategory.CORE
    if confidence >= t["supporting"]:
        return ConceptCategory.SUPPORTING
    if confidence >= t["reference"]:
        return ConceptCategory.REFERENCE
    return None


# ─────────────────────────────────────────────────────────────
# Concept → 기본 카테고리 힌트
#
# detection_stage="direct" (쿼리 직접 매칭)일 때 confidence 기본값 참고용.
# 실제 분류는 _analyze_intent() 반환 confidence 값으로 결정한다.
# ─────────────────────────────────────────────────────────────
CONCEPT_CATEGORY_HINT: dict[str, ConceptCategory] = {
    "CONCEPT_PERSONAL_CREDIT_LOAN":  ConceptCategory.CORE,
    "CONCEPT_INTEREST_RATE":         ConceptCategory.CORE,
    "CONCEPT_REQUIRED_DOCUMENT":     ConceptCategory.CORE,
    "CONCEPT_PREFERENTIAL_RATE":     ConceptCategory.SUPPORTING,
    "CONCEPT_APPLICATION_CONDITION": ConceptCategory.SUPPORTING,
    "CONCEPT_LOAN_PRODUCT":          ConceptCategory.REFERENCE,
    "CONCEPT_POLICY":                ConceptCategory.REFERENCE,
    "CONCEPT_TERMS":                 ConceptCategory.REFERENCE,
    "CONCEPT_COUNSELING_HISTORY":    ConceptCategory.REFERENCE,
    "CONCEPT_CUSTOMER":              ConceptCategory.REFERENCE,
    # 외화 거래
    "CONCEPT_EXCHANGE_RATE":         ConceptCategory.CORE,
    "CONCEPT_CURRENCY_EXCHANGE":     ConceptCategory.CORE,
    "CONCEPT_FOREIGN_REMITTANCE":    ConceptCategory.CORE,
    "CONCEPT_FOREIGN_DEPOSIT":       ConceptCategory.CORE,
    # 알림
    "CONCEPT_NOTIFICATION":          ConceptCategory.CORE,
    "CONCEPT_LOAN_STATUS":           ConceptCategory.SUPPORTING,
}

# detection_stage별 기본 confidence
CONFIDENCE_DIRECT   = 0.90  # 쿼리 키워드 직접 매칭
CONFIDENCE_EXPANDED = 0.70  # 온톨로지 관계 확장

# ─────────────────────────────────────────────────────────────
# Decision Rules
#
# Concept 분류 결과 → Agent 선택 규칙
# leader.py의 _build_decision_v2() 에서 이 목록을 순회한다.
# ─────────────────────────────────────────────────────────────
DECISION_RULES: list[dict] = [
    {
        "rule_id":          "R001",
        "rule_name":        "INTEREST_RATE Core → RATE_AGENT 필수 선택",
        "trigger_concept":  "CONCEPT_INTEREST_RATE",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "RATE_AGENT",
        "tools":            ["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"],
        "role":             "rate_lookup",
        "execution_mode":   "normal",
    },
    {
        "rule_id":          "R002",
        "rule_name":        "REQUIRED_DOCUMENT Core → POLICY_AGENT 필수 선택",
        "trigger_concept":  "CONCEPT_REQUIRED_DOCUMENT",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "POLICY_AGENT",
        "tools":            ["MOCK_DOCUMENT_SEARCH", "MOCK_POLICY_LOOKUP", "MOCK_ELIGIBILITY_CHECK"],
        "role":             "document_and_policy_check",
        "execution_mode":   "normal",
    },
    {
        "rule_id":          "R003",
        "rule_name":        "PREFERENTIAL_RATE Supporting → RATE_RULE_LOOKUP 추가",
        "trigger_concept":  "CONCEPT_PREFERENTIAL_RATE",
        "trigger_category": ConceptCategory.SUPPORTING,
        "required_agent":   "RATE_AGENT",
        "tools":            [],    # RATE_AGENT 내부에서 처리
        "role":             None,  # 기존 RATE_AGENT role 유지
        "execution_mode":   None,
    },
    {
        "rule_id":          "R004",
        "rule_name":        "APPLICATION_CONDITION Supporting → ELIGIBILITY_CHECK 추가",
        "trigger_concept":  "CONCEPT_APPLICATION_CONDITION",
        "trigger_category": ConceptCategory.SUPPORTING,
        "required_agent":   "POLICY_AGENT",
        "tools":            [],
        "role":             None,
        "execution_mode":   None,
    },
    {
        "rule_id":          "R005",
        "rule_name":        "LOAN_PRODUCT Reference → PRODUCT_AGENT 경량 실행",
        "trigger_concept":  "CONCEPT_LOAN_PRODUCT",
        "trigger_category": ConceptCategory.REFERENCE,
        "required_agent":   "PRODUCT_AGENT",
        "tools":            ["MOCK_PRODUCT_LOOKUP"],
        "role":             "product_identification",
        "execution_mode":   "lightweight",
    },
    {
        "rule_id":          "R006",
        "rule_name":        "PERSONAL_CREDIT_LOAN Core → PRODUCT_AGENT 경량 실행",
        "trigger_concept":  "CONCEPT_PERSONAL_CREDIT_LOAN",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "PRODUCT_AGENT",
        "tools":            ["MOCK_PRODUCT_LOOKUP"],
        "role":             "product_identification",
        "execution_mode":   "lightweight",
    },
    {
        "rule_id":          "R007",
        "rule_name":        "SEARCH_AGENT 기본 미선택 — 상담이력 조회 또는 비정형 검색 시에만 선택",
        "trigger_concept":  None,    # 트리거 Concept 없음 (기본 정책)
        "trigger_category": None,
        "required_agent":   None,    # 선택 Agent 없음 (미선택 정책)
        "tools":            [],
        "role":             None,
        "execution_mode":   None,
    },
    # ── 외화 거래 Rules (R008~R011) ──────────────────────────────────
    {
        "rule_id":          "R008",
        "rule_name":        "EXCHANGE_RATE Core → FOREX_AGENT 환율 조회",
        "trigger_concept":  "CONCEPT_EXCHANGE_RATE",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "FOREX_AGENT",
        "tools":            ["MOCK_EXCHANGE_RATE_LOOKUP"],
        "role":             "exchange_rate_lookup",
        "execution_mode":   "normal",
    },
    {
        "rule_id":          "R009",
        "rule_name":        "CURRENCY_EXCHANGE Core → FOREX_AGENT 환전 계산",
        "trigger_concept":  "CONCEPT_CURRENCY_EXCHANGE",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "FOREX_AGENT",
        "tools":            ["MOCK_EXCHANGE_RATE_LOOKUP", "MOCK_CURRENCY_EXCHANGE_CALC"],
        "role":             "currency_exchange_calc",
        "execution_mode":   "normal",
    },
    {
        "rule_id":          "R010",
        "rule_name":        "FOREIGN_REMITTANCE Core → FOREX_AGENT 해외송금 안내",
        "trigger_concept":  "CONCEPT_FOREIGN_REMITTANCE",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "FOREX_AGENT",
        "tools":            ["MOCK_FOREIGN_REMITTANCE", "MOCK_EXCHANGE_RATE_LOOKUP"],
        "role":             "remittance_info",
        "execution_mode":   "normal",
    },
    {
        "rule_id":          "R011",
        "rule_name":        "FOREIGN_DEPOSIT Core → FOREX_AGENT 외화예금 금리 조회",
        "trigger_concept":  "CONCEPT_FOREIGN_DEPOSIT",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "FOREX_AGENT",
        "tools":            ["MOCK_FOREIGN_DEPOSIT_RATE"],
        "role":             "foreign_deposit_rate",
        "execution_mode":   "normal",
    },
    # ── 알림 Rules (R012~R013) ───────────────────────────────────────
    {
        "rule_id":          "R012",
        "rule_name":        "NOTIFICATION Core → NOTIFICATION_AGENT 알림 규칙/발송",
        "trigger_concept":  "CONCEPT_NOTIFICATION",
        "trigger_category": ConceptCategory.CORE,
        "required_agent":   "NOTIFICATION_AGENT",
        "tools":            ["MOCK_NOTIFICATION_RULES", "MOCK_NOTIFICATION_SEND"],
        "role":             "notification_management",
        "execution_mode":   "normal",
    },
    {
        "rule_id":          "R013",
        "rule_name":        "LOAN_STATUS Supporting → NOTIFICATION_AGENT 대출현황 기반 알림",
        "trigger_concept":  "CONCEPT_LOAN_STATUS",
        "trigger_category": ConceptCategory.SUPPORTING,
        "required_agent":   "NOTIFICATION_AGENT",
        "tools":            ["MOCK_NOTIFICATION_RULES"],
        "role":             None,
        "execution_mode":   None,
    },
]

# SEARCH_AGENT를 활성화하는 키워드 목록
SEARCH_AGENT_TRIGGER_KEYWORDS: list[str] = [
    "이전 상담", "상담 이력", "상담이력", "지난번", "저번에",
    "이전에 물어봤", "기록", "history",
]

# ─────────────────────────────────────────────────────────────
# Answer Slot → Concept 매핑
#
# Phase 5 Answer Slot Ranking에서 사용한다.
# slot 이름 → 관련 Concept ID 목록
# ─────────────────────────────────────────────────────────────
SLOT_CONCEPT_MAP: dict[str, list[str]] = {
    "interest_rate":        ["CONCEPT_INTEREST_RATE"],
    "preferential_rate":    ["CONCEPT_PREFERENTIAL_RATE"],
    "required_document":    ["CONCEPT_REQUIRED_DOCUMENT"],
    "application_condition":["CONCEPT_APPLICATION_CONDITION"],
    "loan_product":         ["CONCEPT_LOAN_PRODUCT", "CONCEPT_PERSONAL_CREDIT_LOAN"],
    "policy":               ["CONCEPT_POLICY", "CONCEPT_TERMS"],
    "counseling_history":   ["CONCEPT_COUNSELING_HISTORY"],
    # 외화 거래
    "exchange_rate":        ["CONCEPT_EXCHANGE_RATE"],
    "currency_exchange":    ["CONCEPT_CURRENCY_EXCHANGE"],
    "foreign_remittance":   ["CONCEPT_FOREIGN_REMITTANCE"],
    "foreign_deposit":      ["CONCEPT_FOREIGN_DEPOSIT"],
    # 알림
    "notification":         ["CONCEPT_NOTIFICATION", "CONCEPT_LOAN_STATUS"],
}

# slot 이름 → 사용자에게 보이는 한국어 레이블
SLOT_LABEL_KO: dict[str, str] = {
    "interest_rate":         "금리",
    "preferential_rate":     "우대금리",
    "required_document":     "필요서류",
    "application_condition": "신청조건",
    "loan_product":          "대출상품",
    "policy":                "정책/약관",
    "counseling_history":    "상담이력",
    "exchange_rate":         "환율",
    "currency_exchange":     "환전",
    "foreign_remittance":    "해외송금",
    "foreign_deposit":       "외화예금",
    "notification":          "알림",
}

# slot → 연결 Tool 목록 (Answer Slot Ranking에서 Evidence 후보 수집에 사용)
SLOT_TOOL_MAP: dict[str, list[str]] = {
    "interest_rate":         ["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"],
    "preferential_rate":     ["MOCK_RATE_LOOKUP"],
    "required_document":     ["MOCK_DOCUMENT_SEARCH", "MOCK_POLICY_LOOKUP"],
    "application_condition": ["MOCK_ELIGIBILITY_CHECK"],
    "loan_product":          ["MOCK_PRODUCT_LOOKUP"],
    "policy":                ["MOCK_POLICY_LOOKUP"],
    "counseling_history":    ["MOCK_COUNSELING_HISTORY"],
    "exchange_rate":         ["MOCK_EXCHANGE_RATE_LOOKUP"],
    "currency_exchange":     ["MOCK_EXCHANGE_RATE_LOOKUP", "MOCK_CURRENCY_EXCHANGE_CALC"],
    "foreign_remittance":    ["MOCK_FOREIGN_REMITTANCE"],
    "foreign_deposit":       ["MOCK_FOREIGN_DEPOSIT_RATE"],
    "notification":          ["MOCK_NOTIFICATION_RULES", "MOCK_NOTIFICATION_SEND"],
}

# ─────────────────────────────────────────────────────────────
# Agent 실행 전략
#
# PRODUCT_AGENT는 RATE_AGENT/POLICY_AGENT의 선행 의존성 (product_id 전달)
# ─────────────────────────────────────────────────────────────
AGENT_SERIAL_PREREQUISITE: list[str] = ["PRODUCT_AGENT"]

AGENT_PARALLEL_GROUPS: list[list[str]] = [
    ["RATE_AGENT", "POLICY_AGENT"],
]

# Agent별 기본 execution_mode
AGENT_EXECUTION_MODE: dict[str, str] = {
    "PRODUCT_AGENT":       "lightweight",
    "RATE_AGENT":          "normal",
    "POLICY_AGENT":        "normal",
    "SEARCH_AGENT":        "normal",
    "FOREX_AGENT":         "normal",
    "NOTIFICATION_AGENT":  "normal",
}
