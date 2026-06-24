# evidence_service.py — Evidence 저장 및 근거 간 연결 관리
#
# [이 파일이 하는 두 가지 역할]
#
# 1. 점수 계산 후 저장 (save_evidence_with_score)
#    - evidence_scorer.py 로 신뢰도 점수를 계산한다
#    - EvidenceReference 레코드를 DB에 저장한다
#    - intent 정보를 함께 받아 intent_relevance_score도 기록한다
#
# 2. 근거 간 자동 연결 (link_related_evidence)
#    - 같은 request_id의 Evidence들을 concept 관계(business_concept_relation)로 연결한다
#    - 예: CONCEPT_PERSONAL_CREDIT_LOAN의 근거 ← CONCEPT_INTEREST_RATE의 근거
#          (관계: PERSONAL_CREDIT_LOAN includes INTEREST_RATE)
#    - 연결 방향: 확장된 concept의 근거에 source concept의 근거 ID를 추가한다
#
#    추가로, "같은 상품 ID를 공유하는 근거"도 연결한다.
#    예: 상품 P001의 금리 근거 ↔ 상품 P001의 상품 근거
#
# [호출 시점]
#    executor.py: 각 Tool 호출 직후 save_evidence_with_score() 호출
#    leader.py:   모든 Tool 실행 완료 후 link_related_evidence() 한 번 호출

from sqlalchemy.orm import Session

from app.models.knowledge_model import BusinessConceptRelation
from app.models.trace_model import EvidenceReference
from app.trace.evidence_scorer import score_evidence


def save_evidence_with_score(
    db: Session,
    request_id: str,
    concept_id: str | None,
    source_id: str,           # api_id
    content: dict | list | None,
    intent: str,
    response_latency_ms: int,
    source_type: str = "mock_api",
    agent_id: str | None = None,
) -> EvidenceReference:
    """
    신뢰도를 계산하고 EvidenceReference를 DB에 저장한다.

    [점수 계산 흐름]
    1. evidence_scorer.score_evidence() 로 data_quality, intent_relevance, confidence 계산
    2. 계산 결과를 EvidenceReference 필드에 모두 기록
    3. related_evidence_ids는 아직 비워둔다 (link_related_evidence에서 사후 채움)

    Args:
        source_id           : api_id (예: "MOCK_RATE_LOOKUP")
        content             : API 응답 데이터
        intent              : 사용자 의도 문자열 (예: "INQUIRY")
        response_latency_ms : API 호출에 걸린 시간 (ms)
    """
    # list 응답은 JSON 컬럼에 맞게 dict로 감싸기
    content_dict = content if isinstance(content, dict) else {"data": content}

    scored = score_evidence(
        api_id=source_id,
        data=content_dict,
        intent=intent,
        response_latency_ms=response_latency_ms,
    )

    evidence = EvidenceReference(
        request_id=request_id,
        concept_id=concept_id,
        source_type=source_type,
        source_id=source_id,
        content=content_dict,
        confidence_score=scored.confidence_score,
        data_quality_score=scored.data_quality_score,
        intent_relevance_score=scored.intent_relevance_score,
        response_latency_ms=response_latency_ms,
        item_count=scored.item_count,
        quality_flags=scored.quality_flags,
        related_evidence_ids=None,  # link_related_evidence에서 채움
        agent_id=agent_id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def link_related_evidence(db: Session, request_id: str) -> int:
    """
    같은 request_id 내 Evidence 레코드들을 온톨로지 관계와 공유 상품 ID로 연결한다.

    [연결 방식 1 — concept 온톨로지 관계]
    business_concept_relation 테이블에서 (source→target) 관계를 조회한다.
    target concept의 Evidence에 source concept Evidence의 ID를 추가한다.
    예:
      PERSONAL_CREDIT_LOAN -includes-> INTEREST_RATE (weight=1.0)
      → INTEREST_RATE의 Evidence.related_evidence_ids에 PERSONAL_CREDIT_LOAN의 Evidence ID 추가

    [연결 방식 2 — 공유 상품 ID]
    여러 API 응답에 같은 product_id가 등장하면 서로 연결한다.
    예: MOCK_PRODUCT_LOOKUP의 P001 근거 ↔ MOCK_RATE_LOOKUP의 P001 금리 근거

    반환: 업데이트된 Evidence 레코드 수
    """
    evidences = (
        db.query(EvidenceReference)
        .filter(EvidenceReference.request_id == request_id)
        .all()
    )

    if not evidences:
        return 0

    # concept_id → evidence ID 목록 맵
    concept_to_ev_ids: dict[str, list[int]] = {}
    for ev in evidences:
        if ev.concept_id:
            concept_to_ev_ids.setdefault(ev.concept_id, []).append(ev.id)

    # Evidence ID → 추가할 related IDs 누적 맵
    related_map: dict[int, set[int]] = {ev.id: set() for ev in evidences}

    # ── 연결 방식 1: concept 온톨로지 관계 ──────────────────────
    # 현재 요청에서 사용된 concept ID 목록으로만 관계 조회 (전체 테이블 스캔 방지)
    active_concepts = list(concept_to_ev_ids.keys())
    if active_concepts:
        relations = (
            db.query(BusinessConceptRelation)
            .filter(
                BusinessConceptRelation.source_concept_id.in_(active_concepts),
                BusinessConceptRelation.weight >= 0.7,  # 강한 관계만
            )
            .all()
        )
        for rel in relations:
            # source concept의 Evidence ID들을 target concept Evidence의 related에 추가
            source_ev_ids = concept_to_ev_ids.get(rel.source_concept_id, [])
            target_ev_ids = concept_to_ev_ids.get(rel.target_concept_id, [])
            for target_id in target_ev_ids:
                for src_id in source_ev_ids:
                    if src_id != target_id:
                        related_map[target_id].add(src_id)
            # 역방향도 추가 (양방향 연결)
            for src_id in source_ev_ids:
                for target_id in target_ev_ids:
                    if src_id != target_id:
                        related_map[src_id].add(target_id)

    # ── 연결 방식 2: 공유 상품 ID ─────────────────────────────
    # 각 Evidence의 content에서 product_id 추출 → 같은 product_id 공유 시 연결
    product_to_ev_ids: dict[str, list[int]] = {}
    for ev in evidences:
        content = ev.content or {}
        product_ids = _extract_product_ids(content)
        for pid in product_ids:
            product_to_ev_ids.setdefault(pid, []).append(ev.id)

    for pid, ev_ids in product_to_ev_ids.items():
        if len(ev_ids) > 1:
            # 같은 상품을 참조하는 Evidence끼리 서로 연결
            for ev_id in ev_ids:
                for other_id in ev_ids:
                    if ev_id != other_id:
                        related_map[ev_id].add(other_id)

    # ── DB 업데이트 ──────────────────────────────────────────
    updated = 0
    for ev in evidences:
        new_ids = related_map.get(ev.id, set())
        if new_ids:
            # 기존 related_evidence_ids와 합집합 (중복 방지)
            existing = set(ev.related_evidence_ids or [])
            merged = sorted(existing | new_ids)
            ev.related_evidence_ids = merged
            updated += 1

    if updated:
        db.commit()

    return updated


def _extract_product_ids(content: dict) -> list[str]:
    """
    API 응답 content에서 product_id 값들을 추출한다.

    지원 형태:
    - {"product_id": "P001", ...}                    → ["P001"]
    - {"products": [{"product_id": "P001"}, ...]}    → ["P001", ...]
    - {"rates": [{"product_id": "P001"}, ...]}       → ["P001", ...]
    """
    ids: list[str] = []

    # 최상위 product_id
    if "product_id" in content:
        pid = content["product_id"]
        if pid:
            ids.append(str(pid))

    # 목록 안의 product_id
    for list_key in ["products", "rates", "policies", "documents"]:
        items = content.get(list_key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("product_id"):
                    ids.append(str(item["product_id"]))

    return list(set(ids))  # 중복 제거
