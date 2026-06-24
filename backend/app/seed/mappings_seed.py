from datetime import datetime

from sqlalchemy.orm import Session

from app.models.agent_model import AgentConceptMapping
from app.models.knowledge_model import ConceptApiMapping

AGENT_CONCEPT_MAPPINGS = [
    # PRODUCT_AGENT — 상품/신청조건/고객 담당
    {"agent_id": "PRODUCT_AGENT", "concept_id": "CONCEPT_LOAN_PRODUCT",           "priority": 1},
    {"agent_id": "PRODUCT_AGENT", "concept_id": "CONCEPT_PERSONAL_CREDIT_LOAN",   "priority": 1},
    {"agent_id": "PRODUCT_AGENT", "concept_id": "CONCEPT_CUSTOMER",               "priority": 2},
    {"agent_id": "PRODUCT_AGENT", "concept_id": "CONCEPT_APPLICATION_CONDITION",  "priority": 1},
    # RATE_AGENT — 금리/우대금리/시뮬레이션 담당
    {"agent_id": "RATE_AGENT",    "concept_id": "CONCEPT_INTEREST_RATE",           "priority": 1},
    {"agent_id": "RATE_AGENT",    "concept_id": "CONCEPT_PREFERENTIAL_RATE",       "priority": 1},
    # POLICY_AGENT — 정책/약관/규정/서류 담당 (R002: REQUIRED_DOCUMENT Core → POLICY_AGENT)
    {"agent_id": "POLICY_AGENT",  "concept_id": "CONCEPT_POLICY",                  "priority": 1},
    {"agent_id": "POLICY_AGENT",  "concept_id": "CONCEPT_TERMS",                   "priority": 1},
    {"agent_id": "POLICY_AGENT",  "concept_id": "CONCEPT_REQUIRED_DOCUMENT",       "priority": 1},
    # SEARCH_AGENT — 상담이력 전용 (서류는 POLICY_AGENT 담당이므로 REQUIRED_DOCUMENT 매핑 제거)
    {"agent_id": "SEARCH_AGENT",       "concept_id": "CONCEPT_COUNSELING_HISTORY",   "priority": 1},
    # FOREX_AGENT — 외화 거래 전담
    {"agent_id": "FOREX_AGENT",        "concept_id": "CONCEPT_EXCHANGE_RATE",        "priority": 1},
    {"agent_id": "FOREX_AGENT",        "concept_id": "CONCEPT_FOREIGN_REMITTANCE",   "priority": 1},
    {"agent_id": "FOREX_AGENT",        "concept_id": "CONCEPT_CURRENCY_EXCHANGE",    "priority": 1},
    {"agent_id": "FOREX_AGENT",        "concept_id": "CONCEPT_FOREIGN_DEPOSIT",      "priority": 1},
    # NOTIFICATION_AGENT — 알림/대출현황 담당
    {"agent_id": "NOTIFICATION_AGENT", "concept_id": "CONCEPT_NOTIFICATION",         "priority": 1},
    {"agent_id": "NOTIFICATION_AGENT", "concept_id": "CONCEPT_LOAN_STATUS",          "priority": 1},
]

CONCEPT_API_MAPPINGS = [
    # 상품 관련
    {"concept_id": "CONCEPT_LOAN_PRODUCT",          "api_id": "MOCK_PRODUCT_LOOKUP",      "priority": 1},
    {"concept_id": "CONCEPT_PERSONAL_CREDIT_LOAN",  "api_id": "MOCK_PRODUCT_LOOKUP",      "priority": 1},
    {"concept_id": "CONCEPT_CUSTOMER",              "api_id": "MOCK_PRODUCT_LOOKUP",      "priority": 1},
    {"concept_id": "CONCEPT_APPLICATION_CONDITION", "api_id": "MOCK_ELIGIBILITY_CHECK",   "priority": 1},
    {"concept_id": "CONCEPT_APPLICATION_CONDITION", "api_id": "MOCK_POLICY_LOOKUP",       "priority": 2},
    # 금리 관련
    {"concept_id": "CONCEPT_INTEREST_RATE",         "api_id": "MOCK_RATE_LOOKUP",         "priority": 1},
    {"concept_id": "CONCEPT_INTEREST_RATE",         "api_id": "MOCK_RATE_SIMULATION",     "priority": 2},
    {"concept_id": "CONCEPT_PREFERENTIAL_RATE",     "api_id": "MOCK_RATE_LOOKUP",         "priority": 1},
    # 정책/약관
    {"concept_id": "CONCEPT_POLICY",                "api_id": "MOCK_POLICY_LOOKUP",       "priority": 1},
    {"concept_id": "CONCEPT_TERMS",                 "api_id": "MOCK_POLICY_LOOKUP",       "priority": 1},
    # 서류/이력
    {"concept_id": "CONCEPT_REQUIRED_DOCUMENT",     "api_id": "MOCK_DOCUMENT_SEARCH",              "priority": 1},
    {"concept_id": "CONCEPT_COUNSELING_HISTORY",    "api_id": "MOCK_COUNSELING_HISTORY",            "priority": 1},
    # 개인화 금리 — 신용등급 기반 맞춤 금리 조회
    {"concept_id": "CONCEPT_INTEREST_RATE",         "api_id": "MOCK_PERSONALIZED_RATE_LOOKUP",     "priority": 3},
    # 외화 거래
    {"concept_id": "CONCEPT_EXCHANGE_RATE",         "api_id": "MOCK_EXCHANGE_RATE_LOOKUP",         "priority": 1},
    {"concept_id": "CONCEPT_CURRENCY_EXCHANGE",     "api_id": "MOCK_EXCHANGE_RATE_LOOKUP",         "priority": 1},
    {"concept_id": "CONCEPT_CURRENCY_EXCHANGE",     "api_id": "MOCK_CURRENCY_EXCHANGE_CALC",       "priority": 2},
    {"concept_id": "CONCEPT_FOREIGN_REMITTANCE",    "api_id": "MOCK_FOREIGN_REMITTANCE",           "priority": 1},
    {"concept_id": "CONCEPT_FOREIGN_REMITTANCE",    "api_id": "MOCK_EXCHANGE_RATE_LOOKUP",         "priority": 2},
    {"concept_id": "CONCEPT_FOREIGN_DEPOSIT",       "api_id": "MOCK_FOREIGN_DEPOSIT_RATE",         "priority": 1},
    # 알림
    {"concept_id": "CONCEPT_NOTIFICATION",          "api_id": "MOCK_NOTIFICATION_RULES",           "priority": 1},
    {"concept_id": "CONCEPT_NOTIFICATION",          "api_id": "MOCK_NOTIFICATION_SEND",            "priority": 2},
    {"concept_id": "CONCEPT_LOAN_STATUS",           "api_id": "MOCK_NOTIFICATION_RULES",           "priority": 1},
]


def seed_mappings(db: Session) -> None:
    for m in AGENT_CONCEPT_MAPPINGS:
        existing = (
            db.query(AgentConceptMapping)
            .filter_by(agent_id=m["agent_id"], concept_id=m["concept_id"])
            .first()
        )
        if existing is None:
            db.add(
                AgentConceptMapping(
                    agent_id=m["agent_id"],
                    concept_id=m["concept_id"],
                    priority=m["priority"],
                    created_at=datetime.utcnow(),
                )
            )

    for m in CONCEPT_API_MAPPINGS:
        existing = (
            db.query(ConceptApiMapping)
            .filter_by(concept_id=m["concept_id"], api_id=m["api_id"])
            .first()
        )
        if existing is None:
            db.add(
                ConceptApiMapping(
                    concept_id=m["concept_id"],
                    api_id=m["api_id"],
                    priority=m["priority"],
                    created_at=datetime.utcnow(),
                )
            )

    db.commit()
    print(f"[mappings_seed] {len(AGENT_CONCEPT_MAPPINGS)} agent-concept mappings seeded.")
    print(f"[mappings_seed] {len(CONCEPT_API_MAPPINGS)} concept-api mappings seeded.")
