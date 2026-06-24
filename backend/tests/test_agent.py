# test_agent.py — Agent Registry 라우팅 기능 테스트
#
# agent_registry.py 의 핵심 함수들을 검증한다:
# - get_all_agents: 등록된 Agent 전체 목록 반환
# - route_by_concepts: concept_id 목록을 받아 담당 Agent로 라우팅
#
# 라우팅 규칙: agent_concept_mapping 테이블 기반.
# LLM이 임의로 Agent를 선택하는 것이 아니라 DB의 매핑 데이터를 따른다.

from app.agents.agent_registry import get_all_agents, route_by_concepts


def test_list_agents(db):
    """
    Seed 데이터에 5개 Agent가 있어야 한다:
    LEADER_AGENT, PRODUCT_AGENT, RATE_AGENT, POLICY_AGENT, SEARCH_AGENT
    """
    agents = get_all_agents(db)

    assert len(agents) >= 5
    agent_ids = [a.agent_id for a in agents]
    assert "LEADER_AGENT" in agent_ids


def test_route_by_concepts(db):
    """
    CONCEPT_INTEREST_RATE → RATE_AGENT 로 라우팅되어야 한다.
    routing 결과에 RATE_AGENT의 concept_ids 목록이 포함되어야 한다.
    """
    result = route_by_concepts(db, ["CONCEPT_INTEREST_RATE"])

    assert len(result.routing) >= 1
    routed_agent_ids = [r.agent_id for r in result.routing]
    assert "RATE_AGENT" in routed_agent_ids

    # 라우팅된 항목의 concept_ids에 요청한 concept이 있어야 한다
    rate_route = next(r for r in result.routing if r.agent_id == "RATE_AGENT")
    assert "CONCEPT_INTEREST_RATE" in rate_route.concept_ids


def test_route_empty_concepts(db):
    """
    빈 concept_id 목록을 전달하면 라우팅 결과도 비어 있어야 한다.
    unrouted_concept_ids도 비어 있어야 한다.
    """
    result = route_by_concepts(db, [])

    assert result.routing == []
    assert result.unrouted_concept_ids == []


def test_route_by_concepts_applies_default_agent_order(db):
    """
    입력 concept 순서와 무관하게 기본 Agent 실행 순서를 따른다.

    기본 순서: PRODUCT_AGENT -> RATE_AGENT -> POLICY_AGENT
    SEARCH_AGENT는 CONCEPT_COUNSELING_HISTORY 매핑만 보유하므로
    이 입력 조합에서는 라우팅되지 않는다. (REQUIRED_DOCUMENT는 POLICY_AGENT 담당)
    """
    result = route_by_concepts(
        db,
        [
            "CONCEPT_REQUIRED_DOCUMENT",
            "CONCEPT_POLICY",
            "CONCEPT_INTEREST_RATE",
            "CONCEPT_PERSONAL_CREDIT_LOAN",
        ],
    )

    routed_agent_ids = [route.agent_id for route in result.routing]
    assert routed_agent_ids == [
        "PRODUCT_AGENT",
        "RATE_AGENT",
        "POLICY_AGENT",
    ]


def test_route_by_concepts_only_marks_truly_unrouted_concepts(db):
    """
    unrouted_concept_ids 에는 실제로 매핑되지 않은 concept 만 남아야 한다.
    """
    result = route_by_concepts(
        db,
        ["CONCEPT_INTEREST_RATE", "UNKNOWN_CONCEPT_FOR_TEST"],
    )

    assert [route.agent_id for route in result.routing] == ["RATE_AGENT"]
    assert result.unrouted_concept_ids == ["UNKNOWN_CONCEPT_FOR_TEST"]
