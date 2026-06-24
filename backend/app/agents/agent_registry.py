# agent_registry.py — Agent 조회 및 concept 기반 라우팅 로직
#
# [역할]
#   "어떤 Agent에게 이 질문을 맡겨야 하는가?"를 DB 조회로 결정한다.
#   LLM이 임의로 Agent를 선택하지 않는다 — 반드시 agent_concept_mapping 테이블 기반으로 결정.
#
# [호출 흐름]
#   ai_gateway.py (POST /chat)
#       → LeaderAgent.run()  (agents/leader.py)
#           → route_by_concepts()  ← 이 파일
#               → DB: agent_concept_mapping 테이블 조회
#               → 결과: "RATE_AGENT는 CONCEPT_INTEREST_RATE를 담당"
#   (orchestrator/planner.py 는 deprecated — leader.py 가 직접 처리)
#
# [주요 함수]
#   get_all_agents()     : 전체 활성 Agent 목록 반환 (관리 화면용)
#   get_agent_detail()   : 특정 Agent 상세 + 담당 concept 목록 반환
#   route_by_concepts()  : concept_id 목록을 받아 담당 Agent를 찾아 반환 ← 핵심 함수

from sqlalchemy.orm import Session

from app.models.agent_model import AgentCatalog, AgentConceptMapping
from app.schemas.agent import AgentRouteItem, AgentRouteResponse


DEFAULT_AGENT_EXECUTION_ORDER = [
    "PRODUCT_AGENT",
    "RATE_AGENT",
    "POLICY_AGENT",
    "SEARCH_AGENT",
    "FOREX_AGENT",
    "NOTIFICATION_AGENT",
]


def get_all_agents(db: Session) -> list[AgentCatalog]:
    """
    활성화된 전체 Agent 목록을 반환한다.

    LEADER_AGENT도 포함해서 반환한다.
    concept 매핑이 없어도 registry에는 존재해야 하기 때문이다.
    (LEADER_AGENT는 직접 concept을 처리하지 않고 Sub-Agent를 조율하는 역할)
    """
    return db.query(AgentCatalog).filter(AgentCatalog.is_active == True).all()  # noqa: E712


def get_agent_detail(
    db: Session, agent_id: str
) -> tuple[AgentCatalog, list[str]] | None:
    """
    특정 Agent의 상세 정보와 담당 concept_id 목록을 반환한다.

    반환값: (AgentCatalog 객체, [concept_id, ...]) 튜플
    Agent가 없으면 None 반환.

    concept_id 목록은 Leader Agent가 "이 Sub-Agent가 어떤 업무를 처리할 수 있는지"
    파악할 때 참조한다.
    """
    agent = (
        db.query(AgentCatalog)
        .filter(AgentCatalog.agent_id == agent_id, AgentCatalog.is_active == True)  # noqa: E712
        .first()
    )
    if agent is None:
        return None

    # priority 오름차순 정렬 — 숫자가 낮을수록 우선순위가 높은 concept이다
    mappings = (
        db.query(AgentConceptMapping)
        .filter(AgentConceptMapping.agent_id == agent_id)
        .order_by(AgentConceptMapping.priority)
        .all()
    )
    concept_ids = [m.concept_id for m in mappings]
    return agent, concept_ids


def route_by_concepts(db: Session, concept_ids: list[str]) -> AgentRouteResponse:
    """
    탐지된 concept_id 목록을 받아 각 concept을 담당하는 Agent를 찾아 반환한다.

    [동작 원리]
    - concept_id마다 agent_concept_mapping 테이블을 조회해 담당 Agent를 찾는다.
    - 같은 Agent가 여러 concept을 담당하면 하나의 AgentRouteItem으로 합산한다.
      예: RATE_AGENT가 CONCEPT_INTEREST_RATE, CONCEPT_PREFERENTIAL_RATE 모두 담당하면
          AgentRouteItem(agent_id="RATE_AGENT", concept_ids=["CONCEPT_INTEREST_RATE", "CONCEPT_PREFERENTIAL_RATE"])

    [반환값]
    - AgentRouteResponse.routing      : 라우팅된 Agent 목록
    - AgentRouteResponse.unrouted_concept_ids : 담당 Agent가 없는 concept 목록
      → unrouted_concept_ids가 있으면 Leader Agent가 처리 방법을 별도 결정해야 한다

    [중요] priority가 가장 낮은(=높은 우선순위) Agent 1개만 선택한다.
    동일 concept에 여러 Agent가 매핑된 경우 우선순위 1위만 라우팅된다.
    """
    # key: agent_id, value: 이 Agent가 담당하는 concept_id 목록
    agent_concept_map: dict[str, list[str]] = {}

    for concept_id in concept_ids:
        # priority 오름차순 첫 번째 = 우선순위가 가장 높은 Agent
        mapping = (
            db.query(AgentConceptMapping)
            .filter(AgentConceptMapping.concept_id == concept_id)
            .order_by(AgentConceptMapping.priority)
            .first()
        )
        if mapping:
            # 이미 이 Agent에 다른 concept이 있으면 추가, 없으면 새 목록 생성
            agent_concept_map.setdefault(mapping.agent_id, []).append(concept_id)

    routed_agent_ids = sorted(
        agent_concept_map.keys(),
        key=lambda agent_id: (
            DEFAULT_AGENT_EXECUTION_ORDER.index(agent_id)
            if agent_id in DEFAULT_AGENT_EXECUTION_ORDER
            else len(DEFAULT_AGENT_EXECUTION_ORDER)
        ),
    )

    # agent_id → AgentCatalog 객체로 변환 (한 번에 IN 쿼리)
    agents_map = {
        a.agent_id: a
        for a in db.query(AgentCatalog)
        .filter(AgentCatalog.agent_id.in_(routed_agent_ids))
        .all()
    }

    routing = [
        AgentRouteItem(
            agent_id=aid,
            agent_type=agents_map[aid].agent_type,
            name=agents_map[aid].name,
            concept_ids=agent_concept_map[aid],
        )
        for aid in routed_agent_ids
        if aid in agents_map  # DB에서 삭제된 Agent는 안전하게 건너뜀
    ]

    # 매핑된 Agent가 없는 concept — 추후 Leader Agent 처리 또는 "알 수 없음" 응답
    routed_concept_ids = {
        concept_id
        for routed_concepts in agent_concept_map.values()
        for concept_id in routed_concepts
    }
    unrouted = [cid for cid in concept_ids if cid not in routed_concept_ids]

    return AgentRouteResponse(routing=routing, unrouted_concept_ids=unrouted)
