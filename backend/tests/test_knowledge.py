# test_knowledge.py — 업무 지식 모델 검색 기능 테스트
#
# concept_service.py 의 핵심 함수들을 검증한다:
# - search_concepts: 키워드로 BusinessConcept 검색 (이름 + alias 모두 검색)
# - get_agents_by_concept: concept에 매핑된 Agent 목록 반환
# - get_apis_by_concept: concept에 매핑된 API(Tool) 목록 반환
#
# 이 테스트들은 Seed 데이터가 등록된 상태에서만 통과한다.
# Seed 미등록 시: python -m app.seed.run_seed 먼저 실행

from uuid import uuid4

from app.knowledge.concept_service import (
    detect_concepts_in_message,
    get_agents_by_concept,
    get_apis_by_concept,
    search_concepts,
)


def test_search_by_keyword_rate(db):
    """
    "금리" 키워드로 검색하면 CONCEPT_INTEREST_RATE가 결과에 포함되어야 한다.
    Seed 데이터에 "금리" 이름의 BusinessConcept가 있기 때문이다.
    """
    results = search_concepts(db, "금리")

    concept_ids = [c.concept_id for c in results]
    assert "CONCEPT_INTEREST_RATE" in concept_ids


def test_search_by_alias(db):
    """
    alias 테이블에 등록된 단어로도 concept을 찾을 수 있어야 한다.
    예: "이자율" → "금리" concept (alias로 등록된 경우)
    alias 미등록 시 결과 0건이므로, 검색 자체가 오류 없이 동작하는지만 확인한다.
    """
    results = search_concepts(db, "신용")

    # 검색 결과가 있으면 BusinessConcept 객체여야 한다
    for concept in results:
        assert concept.concept_id is not None
        assert concept.name is not None


def test_agents_by_concept(db):
    """
    CONCEPT_INTEREST_RATE에 매핑된 Agent 목록에 RATE_AGENT가 있어야 한다.
    Seed 데이터의 agent_concept_mapping 테이블에 정의된 관계를 검증한다.
    """
    agents = get_agents_by_concept(db, "CONCEPT_INTEREST_RATE")

    agent_ids = [a.agent_id for a in agents]
    assert "RATE_AGENT" in agent_ids


def test_apis_by_concept(db):
    """
    CONCEPT_INTEREST_RATE에 매핑된 API 목록에 MOCK_RATE_LOOKUP이 있어야 한다.
    Orchestrator는 이 매핑을 기반으로 실행할 Tool을 결정한다.
    """
    apis = get_apis_by_concept(db, "CONCEPT_INTEREST_RATE")

    api_ids = [a.api_id for a in apis]
    assert "MOCK_RATE_LOOKUP" in api_ids


def test_get_concept_detail(client):
    resp = client.get("/api/v1/knowledge/concepts/CONCEPT_INTEREST_RATE")

    assert resp.status_code == 200
    body = resp.json()
    assert body["concept_id"] == "CONCEPT_INTEREST_RATE"
    assert "aliases" in body


def test_create_and_update_concept(client, db):
    concept_id = f"CONCEPT_TEST_{uuid4().hex[:8]}"
    create_resp = client.post(
        "/api/v1/knowledge/concepts",
        json={
            "concept_id": concept_id,
            "name": "관리 테스트 개념",
            "description": "등록 테스트",
            "domain": "ADMIN",
            "is_active": True,
            "aliases": ["테스트개념", "관리테스트"],
        },
    )

    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["concept_id"] == concept_id
    assert created["aliases"] == ["테스트개념", "관리테스트"]

    update_resp = client.put(
        f"/api/v1/knowledge/concepts/{concept_id}",
        json={
            "name": "관리 테스트 개념 수정",
            "description": "수정 테스트",
            "domain": "OPS",
            "is_active": False,
            "aliases": ["수정별칭"],
        },
    )

    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["name"] == "관리 테스트 개념 수정"
    assert updated["domain"] == "OPS"
    assert updated["is_active"] is False
    assert updated["aliases"] == ["수정별칭"]

    client.delete(f"/api/v1/knowledge/concepts/{concept_id}")


def test_create_and_update_alias(client):
    create_resp = client.post(
        "/api/v1/knowledge/aliases",
        json={
            "concept_id": "CONCEPT_INTEREST_RATE",
            "alias": "금리테스트별칭",
            "language": "ko",
        },
    )

    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["concept_id"] == "CONCEPT_INTEREST_RATE"
    assert created["alias"] == "금리테스트별칭"

    update_resp = client.put(
        f"/api/v1/knowledge/aliases/{created['id']}",
        json={
            "alias": "금리수정별칭",
            "language": "ko",
        },
    )

    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["alias"] == "금리수정별칭"


def test_create_and_update_relation(client):
    create_resp = client.post(
        "/api/v1/knowledge/relations",
        json={
            "source_concept_id": "CONCEPT_LOAN_PRODUCT",
            "target_concept_id": "CONCEPT_INTEREST_RATE",
            "relation_type": "RELATED_TO",
            "weight": 0.75,
        },
    )

    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["source_concept_id"] == "CONCEPT_LOAN_PRODUCT"
    assert created["target_concept_id"] == "CONCEPT_INTEREST_RATE"

    update_resp = client.put(
        f"/api/v1/knowledge/relations/{created['id']}",
        json={
            "source_concept_id": "CONCEPT_PERSONAL_CREDIT_LOAN",
            "target_concept_id": "CONCEPT_REQUIRED_DOCUMENT",
            "relation_type": "REQUIRES",
            "weight": 0.9,
        },
    )

    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["relation_type"] == "REQUIRES"
    assert updated["weight"] == 0.9


def test_create_and_update_agent_mapping(client):
    create_resp = client.post(
        "/api/v1/knowledge/agent-mappings",
        json={
            "agent_id": "RATE_AGENT",
            "concept_id": "CONCEPT_POLICY",
            "priority": 2,
        },
    )

    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["agent_id"] == "RATE_AGENT"
    assert created["concept_id"] == "CONCEPT_POLICY"

    update_resp = client.put(
        f"/api/v1/knowledge/agent-mappings/{created['id']}",
        json={
            "agent_id": "RATE_AGENT",
            "concept_id": "CONCEPT_POLICY",
            "priority": 3,
        },
    )

    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["agent_id"] == "RATE_AGENT"
    assert updated["priority"] == 3

    client.delete(f"/api/v1/knowledge/agent-mappings/{created['id']}")


def test_create_and_update_concept_api_mapping(client):
    create_resp = client.post(
        "/api/v1/knowledge/concept-api-mappings",
        json={
            "concept_id": "CONCEPT_REQUIRED_DOCUMENT",
            "api_id": "MOCK_DOCUMENT_SEARCH",
            "priority": 3,
        },
    )

    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["concept_id"] == "CONCEPT_REQUIRED_DOCUMENT"
    assert created["api_id"] == "MOCK_DOCUMENT_SEARCH"

    update_resp = client.put(
        f"/api/v1/knowledge/concept-api-mappings/{created['id']}",
        json={
            "concept_id": "CONCEPT_REQUIRED_DOCUMENT",
            "api_id": "MOCK_POLICY_LOOKUP",
            "priority": 0,
        },
    )

    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["api_id"] == "MOCK_POLICY_LOOKUP"
    assert updated["priority"] == 0


def test_delete_alias_relation_and_mappings(client):
    alias_resp = client.post(
        "/api/v1/knowledge/aliases",
        json={
            "concept_id": "CONCEPT_INTEREST_RATE",
            "alias": "삭제테스트별칭",
            "language": "ko",
        },
    )
    relation_resp = client.post(
        "/api/v1/knowledge/relations",
        json={
            "source_concept_id": "CONCEPT_LOAN_PRODUCT",
            "target_concept_id": "CONCEPT_INTEREST_RATE",
            "relation_type": "DELETE_TEST",
            "weight": 0.5,
        },
    )
    agent_mapping_resp = client.post(
        "/api/v1/knowledge/agent-mappings",
        json={
            "agent_id": "RATE_AGENT",
            "concept_id": "CONCEPT_TERMS",
            "priority": 4,
        },
    )
    api_mapping_resp = client.post(
        "/api/v1/knowledge/concept-api-mappings",
        json={
            "concept_id": "CONCEPT_REQUIRED_DOCUMENT",
            "api_id": "MOCK_DOCUMENT_SEARCH",
            "priority": 4,
        },
    )

    assert client.delete(f"/api/v1/knowledge/aliases/{alias_resp.json()['id']}").status_code == 204
    assert client.delete(f"/api/v1/knowledge/relations/{relation_resp.json()['id']}").status_code == 204
    assert client.delete(f"/api/v1/knowledge/agent-mappings/{agent_mapping_resp.json()['id']}").status_code == 204
    assert client.delete(f"/api/v1/knowledge/concept-api-mappings/{api_mapping_resp.json()['id']}").status_code == 204


# ── detect_concepts_in_message 단위 테스트 ───────────────────────────
#
# alias가 메시지에 실제로 포함되는지(정방향) 검증한다.
# 역방향 오탐(alias가 keyword를 포함하는지) 방지 로직이 핵심.
# Seed alias 기준:
#   "달러" → CONCEPT_EXCHANGE_RATE
#   "달러예금" → CONCEPT_FOREIGN_DEPOSIT   ("달러"만으로는 FOREIGN_DEPOSIT 탐지 안 됨)
#   "달러환전" → CONCEPT_CURRENCY_EXCHANGE  ("달러"만으로는 CURRENCY_EXCHANGE 탐지 안 됨)
#   "환율" → CONCEPT_EXCHANGE_RATE
#   "환전" → CONCEPT_CURRENCY_EXCHANGE
#   "해외송금" → CONCEPT_FOREIGN_REMITTANCE
#   "외화예금" → CONCEPT_FOREIGN_DEPOSIT
#   "금리" → CONCEPT_INTEREST_RATE
#   "신용대출" → CONCEPT_PERSONAL_CREDIT_LOAN
#   "알림" → CONCEPT_NOTIFICATION
#   "만기" → CONCEPT_LOAN_STATUS

def _cids(concepts) -> set[str]:
    return {c.concept_id for c in concepts}


def test_detect_loan_rate_query(db):
    """
    "신용대출 금리 알려줘" → 대출상품 + 금리 두 concept 모두 탐지돼야 한다.
    """
    result = _cids(detect_concepts_in_message(db, "신용대출 금리 알려줘"))
    assert "CONCEPT_PERSONAL_CREDIT_LOAN" in result
    assert "CONCEPT_INTEREST_RATE" in result


def test_detect_exchange_rate_query(db):
    """
    "오늘 달러 환율 알려줘" → EXCHANGE_RATE만 탐지. 외화예금·환전은 탐지 안 됨.
    """
    result = _cids(detect_concepts_in_message(db, "오늘 달러 환율 알려줘"))
    assert "CONCEPT_EXCHANGE_RATE" in result
    assert "CONCEPT_FOREIGN_DEPOSIT" not in result
    assert "CONCEPT_CURRENCY_EXCHANGE" not in result


def test_detect_no_false_positive_dollar_alone(db):
    """
    [역방향 오탐 방지 회귀 테스트]
    "달러 환율" 쿼리는 "달러예금"·"달러환전" alias를 역방향으로 잘못 탐지하면 안 된다.
    detect_concepts_in_message 도입 이전에는 search_concepts("달러")가
    EXCHANGE_RATE + CURRENCY_EXCHANGE + FOREIGN_DEPOSIT 세 개를 반환했다.
    """
    result = _cids(detect_concepts_in_message(db, "달러 환율"))
    assert "CONCEPT_EXCHANGE_RATE" in result
    # "달러환전", "달러예금" alias가 "달러 환율" 메시지에 없으므로 탐지 금지
    assert "CONCEPT_CURRENCY_EXCHANGE" not in result
    assert "CONCEPT_FOREIGN_DEPOSIT" not in result


def test_detect_currency_exchange_query(db):
    """
    "달러 환전 신청하고 싶어" → EXCHANGE_RATE + CURRENCY_EXCHANGE 모두 탐지.
    "달러" alias → EXCHANGE_RATE, "환전" alias → CURRENCY_EXCHANGE
    """
    result = _cids(detect_concepts_in_message(db, "달러 환전 신청하고 싶어"))
    assert "CONCEPT_EXCHANGE_RATE" in result
    assert "CONCEPT_CURRENCY_EXCHANGE" in result


def test_detect_remittance_query(db):
    """
    "미국으로 해외송금 하려고" → FOREIGN_REMITTANCE 탐지.
    """
    result = _cids(detect_concepts_in_message(db, "미국으로 해외송금 하려고"))
    assert "CONCEPT_FOREIGN_REMITTANCE" in result


def test_detect_foreign_deposit_query(db):
    """
    "외화예금 계좌 만들고 싶어" → FOREIGN_DEPOSIT만 탐지. 환율은 탐지 안 됨.
    "달러" 단어가 메시지에 없으므로 EXCHANGE_RATE는 탐지되면 안 된다.
    """
    result = _cids(detect_concepts_in_message(db, "외화예금 계좌 만들고 싶어"))
    assert "CONCEPT_FOREIGN_DEPOSIT" in result
    assert "CONCEPT_EXCHANGE_RATE" not in result


def test_detect_notification_with_maturity(db):
    """
    "대출 만기 알림 받고 싶어" → NOTIFICATION + LOAN_STATUS 모두 탐지.
    "알림" alias → NOTIFICATION, "만기" alias → LOAN_STATUS
    """
    result = _cids(detect_concepts_in_message(db, "대출 만기 알림 받고 싶어"))
    assert "CONCEPT_NOTIFICATION" in result
    assert "CONCEPT_LOAN_STATUS" in result


def test_detect_required_document_query(db):
    """
    "신용대출 필요서류 알려줘" → PERSONAL_CREDIT_LOAN + REQUIRED_DOCUMENT.
    """
    result = _cids(detect_concepts_in_message(db, "신용대출 필요서류 알려줘"))
    assert "CONCEPT_PERSONAL_CREDIT_LOAN" in result
    assert "CONCEPT_REQUIRED_DOCUMENT" in result


def test_detect_empty_message(db):
    """빈 메시지 → 빈 결과. 오류 없이 처리돼야 한다."""
    assert detect_concepts_in_message(db, "") == []
    assert detect_concepts_in_message(db, "   ") == []


def test_detect_no_alias_match(db):
    """
    등록된 alias가 없는 일반 인사말 → 빈 결과.
    """
    result = detect_concepts_in_message(db, "안녕하세요 잘 부탁합니다")
    assert result == []


def test_detect_counseling_history_query(db):
    """
    "이전 상담 이력 보여줘" → COUNSELING_HISTORY 탐지.
    "상담이력" alias가 메시지 안에 포함돼 있어야 탐지된다.
    """
    result = _cids(detect_concepts_in_message(db, "이전 상담이력 보여줘"))
    assert "CONCEPT_COUNSELING_HISTORY" in result


def test_detect_usd_alias(db):
    """
    "USD 환율 조회" → EXCHANGE_RATE 탐지 ("USD" alias 등록 여부 확인).
    """
    result = _cids(detect_concepts_in_message(db, "USD 환율 조회"))
    assert "CONCEPT_EXCHANGE_RATE" in result


def test_delete_concept_cascades_related_rows(client):
    concept_id = "CONCEPT_DELETE_TEST"
    create_resp = client.post(
        "/api/v1/knowledge/concepts",
        json={
            "concept_id": concept_id,
            "name": "삭제 테스트 개념",
            "description": "delete cascade",
            "domain": "TEST",
            "is_active": True,
            "aliases": ["삭제별칭"],
        },
    )
    assert create_resp.status_code == 201, create_resp.text

    relation_resp = client.post(
        "/api/v1/knowledge/relations",
        json={
            "source_concept_id": concept_id,
            "target_concept_id": "CONCEPT_INTEREST_RATE",
            "relation_type": "DELETE_TEST",
            "weight": 1.0,
        },
    )
    agent_mapping_resp = client.post(
        "/api/v1/knowledge/agent-mappings",
        json={
            "agent_id": "RATE_AGENT",
            "concept_id": concept_id,
            "priority": 0,
        },
    )
    api_mapping_resp = client.post(
        "/api/v1/knowledge/concept-api-mappings",
        json={
            "concept_id": concept_id,
            "api_id": "MOCK_RATE_LOOKUP",
            "priority": 0,
        },
    )
    assert relation_resp.status_code == 201
    assert agent_mapping_resp.status_code == 201
    assert api_mapping_resp.status_code == 201

    delete_resp = client.delete(f"/api/v1/knowledge/concepts/{concept_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    get_resp = client.get(f"/api/v1/knowledge/concepts/{concept_id}")
    assert get_resp.status_code == 404
