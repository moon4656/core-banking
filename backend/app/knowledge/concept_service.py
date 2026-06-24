# concept_service.py — 업무 개념(Concept) 조회 서비스
#
# [역할]
#   BusinessConcept 관련 DB 쿼리를 한 곳에서 관리한다.
#   라우터(api/routes/knowledge.py)와 Leader Agent가 이 함수를 호출한다.
#
# [캐싱 전략]
#   search_concepts() 는 Leader Agent가 메시지의 각 단어마다 호출한다.
#   같은 keyword 를 여러 요청에서 반복 조회하므로 Redis 에 5분 TTL 로 캐싱한다.
#   Redis 장애 시 DB 직접 조회로 fallback — 서비스 중단 없음.
#   캐시 키: "concept:search:<keyword_lower>"
#   캐시 값: concept_id 목록 JSON — ORM 객체 대신 ID 만 저장해 직렬화 문제 회피

import json

import redis as redis_lib
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_model import AgentCatalog, AgentConceptMapping
from app.models.knowledge_model import (
    ApiCatalog,
    BusinessConcept,
    BusinessTermAlias,
    ConceptApiMapping,
)

_CONCEPT_CACHE_TTL = 300  # 5분 — concept/alias 는 자주 바뀌지 않는다


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def get_all_concepts(db: Session) -> list[BusinessConcept]:
    """
    활성화된 전체 업무 개념(Concept) 목록을 반환한다.

    비활성(is_active=False) concept은 운영 중 deprecated된 개념이므로 클라이언트에 노출하지 않는다.
    """
    return db.query(BusinessConcept).filter(BusinessConcept.is_active == True).all()  # noqa: E712


def search_concepts(db: Session, keyword: str) -> list[BusinessConcept]:
    """
    키워드로 concept을 검색한다. concept 이름과 alias(별칭) 테이블을 함께 검색한다.

    [캐싱]
    Redis에 concept_id 목록을 5분 TTL 로 저장한다.
    캐시 히트 시 DB에는 concept_id IN(...) 단일 쿼리만 실행한다.
    Redis 장애 또는 empty keyword 는 DB 직접 조회로 fallback한다.

    [ilike 사용 이유]
    대소문자 구분 없이 부분 일치 검색 (예: "금리" → "기준금리", "대출금리" 모두 매칭)

    반환: 중복 없는 BusinessConcept 목록 (이름 매칭 + alias 매칭 합집합)
    """
    if not keyword or not keyword.strip():
        return []

    cache_key = f"concept:search:{keyword.strip().lower()}"

    # ── Redis 캐시 시도 ──────────────────────────────────────
    try:
        client = _get_redis()
        cached = client.get(cache_key)
        if cached:
            concept_ids: list[str] = json.loads(cached)
            if not concept_ids:
                return []
            return (
                db.query(BusinessConcept)
                .filter(
                    BusinessConcept.concept_id.in_(concept_ids),
                    BusinessConcept.is_active == True,  # noqa: E712
                )
                .all()
            )
    except Exception:
        pass  # Redis 장애 → DB 직접 조회

    # ── DB 조회 (캐시 미스 또는 Redis 장애) ──────────────────
    pattern = f"%{keyword.strip()}%"

    # 1) concept 이름으로 직접 검색
    by_name = (
        db.query(BusinessConcept)
        .filter(BusinessConcept.name.ilike(pattern), BusinessConcept.is_active == True)  # noqa: E712
        .all()
    )

    # 2) alias 테이블에서 키워드와 일치하는 concept 검색 — JOIN 방식
    by_alias = (
        db.query(BusinessConcept)
        .join(
            BusinessTermAlias,
            BusinessTermAlias.concept_id == BusinessConcept.concept_id,
        )
        .filter(
            BusinessTermAlias.alias.ilike(pattern),
            BusinessConcept.is_active == True,  # noqa: E712
        )
        .all()
    )

    # 3) 이름 매칭 + alias 매칭 결과를 합치되, 중복 concept은 한 번만 포함
    seen: set[str] = set()
    result: list[BusinessConcept] = []
    for concept in by_name + by_alias:
        if concept.concept_id not in seen:
            seen.add(concept.concept_id)
            result.append(concept)

    # ── 결과를 Redis에 캐시 (빈 결과는 캐시하지 않음) ────────
    # 빈 결과를 캐시하면, 이후 alias가 추가되거나 DB가 변경돼도
    # TTL 만료 전까지 계속 빈 결과를 반환하는 캐시 오염이 발생한다.
    if result:
        try:
            client = _get_redis()
            ids_to_cache = [c.concept_id for c in result]
            client.setex(cache_key, _CONCEPT_CACHE_TTL, json.dumps(ids_to_cache))
        except Exception:
            pass  # 캐시 저장 실패는 무시

    return result


def detect_concepts_in_message(db: Session, message: str) -> list[BusinessConcept]:
    """
    메시지에 alias가 포함되어 있는지를 검사해 concept을 탐지한다.

    [기존 search_concepts와 차이점]
    - search_concepts : alias ILIKE '%keyword%'  → alias가 keyword를 포함하는지 확인
    - 이 함수         : alias IN message          → 메시지가 alias를 포함하는지 확인 (정방향)

    정방향 매칭이 맞는 이유:
    - "달러" 검색 시 search_concepts는 "달러예금", "달러환전" alias도 모두 매칭됨 (역방향 오탐)
    - 이 함수는 메시지 "달러 환율 알려줘"에 "달러", "환율"만 실제로 존재하므로 정확히 매칭

    긴 alias를 먼저 검사해 구체적 alias가 우선 매칭되게 한다.
    예) "중금리 사잇돌2"(8자)가 "사잇돌"(3자)보다 먼저 검사됨.
    """
    if not message or not message.strip():
        return []

    rows = (
        db.query(BusinessTermAlias, BusinessConcept)
        .join(BusinessConcept, BusinessConcept.concept_id == BusinessTermAlias.concept_id)
        .filter(BusinessConcept.is_active == True)  # noqa: E712
        .all()
    )
    rows.sort(key=lambda r: len(r[0].alias), reverse=True)

    msg_lower = message.lower()
    seen: set[str] = set()
    result: list[BusinessConcept] = []
    for alias_row, concept in rows:
        if alias_row.alias.lower() in msg_lower and concept.concept_id not in seen:
            seen.add(concept.concept_id)
            result.append(concept)
    return result


def get_agents_by_concept(db: Session, concept_id: str) -> list[AgentCatalog]:
    """
    특정 concept을 담당하는 Agent 목록을 priority 순으로 반환한다.

    priority 오름차순 정렬 — 숫자가 낮을수록 Leader Agent가 먼저 선택하는 Sub-Agent다.
    예: RATE_AGENT(priority=0), SEARCH_AGENT(priority=1) → RATE_AGENT가 먼저 선택됨
    """
    rows = (
        db.query(AgentConceptMapping)
        .filter(AgentConceptMapping.concept_id == concept_id)
        .order_by(AgentConceptMapping.priority)
        .all()
    )
    agent_ids = [r.agent_id for r in rows]
    if not agent_ids:
        return []

    # IN 쿼리로 한 번에 조회한 뒤, 원래 priority 순서를 유지하며 정렬
    agents_map = {
        a.agent_id: a
        for a in db.query(AgentCatalog)
        .filter(AgentCatalog.agent_id.in_(agent_ids), AgentCatalog.is_active == True)  # noqa: E712
        .all()
    }
    # agent_ids 순서(=priority 순서)를 유지하면서 반환 — IN 쿼리는 순서를 보장하지 않는다
    return [agents_map[aid] for aid in agent_ids if aid in agents_map]


def get_apis_by_concept(db: Session, concept_id: str) -> list[ApiCatalog]:
    """
    특정 concept에 매핑된 API 목록을 priority 순으로 반환한다.

    priority 오름차순 정렬 — Tool Hub가 이 순서대로 실제 호출할 API를 선택한다.
    Planner가 ExecutionStep을 만들 때 이 함수를 호출한다.
    """
    rows = (
        db.query(ConceptApiMapping)
        .filter(ConceptApiMapping.concept_id == concept_id)
        .order_by(ConceptApiMapping.priority)
        .all()
    )
    api_ids = [r.api_id for r in rows]
    if not api_ids:
        return []

    apis_map = {
        a.api_id: a
        for a in db.query(ApiCatalog)
        .filter(ApiCatalog.api_id.in_(api_ids), ApiCatalog.is_active == True)  # noqa: E712
        .all()
    }
    # api_ids 순서(=priority 순서)를 유지하면서 반환
    return [apis_map[aid] for aid in api_ids if aid in apis_map]
