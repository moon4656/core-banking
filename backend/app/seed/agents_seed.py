from datetime import datetime

from sqlalchemy.orm import Session

from app.models.agent_model import AgentCatalog

AGENTS = [
    {
        "agent_id": "LEADER_AGENT",
        "name": "리더 에이전트",
        "agent_type": "leader",
        "description": "사용자 요청을 분석하고 적절한 Sub-Agent로 라우팅하는 오케스트레이터",
        "capabilities": ["request_analysis", "agent_routing", "response_aggregation"],
    },
    {
        "agent_id": "PRODUCT_AGENT",
        "name": "상품 에이전트",
        "agent_type": "product",
        "description": "대출 상품 정보 조회 및 추천을 담당하는 에이전트",
        "capabilities": ["product_lookup", "product_recommendation", "condition_check"],
    },
    {
        "agent_id": "RATE_AGENT",
        "name": "금리 에이전트",
        "agent_type": "rate",
        "description": "금리 및 우대금리 정보 조회와 계산을 담당하는 에이전트",
        "capabilities": ["rate_lookup", "preferential_rate_calc", "rate_comparison"],
    },
    {
        "agent_id": "POLICY_AGENT",
        "name": "정책 에이전트",
        "agent_type": "policy",
        "description": "대출 정책, 약관, 규정 정보 조회를 담당하는 에이전트",
        "capabilities": ["policy_lookup", "terms_lookup", "regulation_check"],
    },
    {
        "agent_id": "SEARCH_AGENT",
        "name": "검색 에이전트",
        "agent_type": "search",
        "description": "필요서류 및 상담이력 등 문서 검색을 담당하는 에이전트",
        "capabilities": ["document_search", "history_lookup", "keyword_search"],
    },
    {
        "agent_id": "FOREX_AGENT",
        "name": "외화 거래 에이전트",
        "agent_type": "forex",
        "description": "환율 조회, 외화 환전 계산, 해외송금, 외화예금 금리 정보를 담당하는 에이전트",
        "capabilities": ["exchange_rate_lookup", "currency_exchange_calc", "foreign_remittance", "foreign_deposit_rate"],
    },
    {
        "agent_id": "NOTIFICATION_AGENT",
        "name": "알림 에이전트",
        "agent_type": "notification",
        "description": "대출 금리변동·만기·연체·한도소진 등 고객 알림 규칙 조회 및 발송을 담당하는 에이전트",
        "capabilities": ["notification_rules_lookup", "notification_send", "loan_status_alert"],
    },
]


def seed_agents(db: Session) -> None:
    for data in AGENTS:
        existing = db.query(AgentCatalog).filter_by(agent_id=data["agent_id"]).first()
        if existing is None:
            db.add(
                AgentCatalog(
                    agent_id=data["agent_id"],
                    name=data["name"],
                    agent_type=data["agent_type"],
                    description=data["description"],
                    capabilities=data["capabilities"],
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
            )

    db.commit()
    print(f"[agents_seed] {len(AGENTS)} agents seeded.")
