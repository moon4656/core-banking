# relations_seed.py — 업무 개념 간 관계(온톨로지) 초기 데이터
#
# [관계 의미]
#   source_concept_id → target_concept_id
#   사용자가 하나의 concept을 언급하면 관련 concept까지 자동 확장한다.
#
# [relation_type 값]
#   "includes"     : 상위 개념이 하위 개념을 포함 (신용대출 → 금리)
#   "requires"     : 신청 시 필요 (신용대출 → 필요서류)
#   "governed_by"  : 규정/정책에 의해 지배됨 (신용대출 → 정책)
#   "has_condition": 조건을 가짐 (대출상품 → 신청조건)
#   "has_record"   : 이력을 보유 (고객 → 상담이력)
#
# [weight]
#   1.0 = 강한 연관 / 0.7 이상만 온톨로지 확장에 사용 (_expand_via_relations 임계값)

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge_model import BusinessConceptRelation

RELATIONS = [
    # ── 대출상품 ──────────────────────────────────────────────
    # 대출상품은 개인신용대출을 포함한다
    {"source": "CONCEPT_LOAN_PRODUCT", "target": "CONCEPT_PERSONAL_CREDIT_LOAN",
     "relation_type": "includes",     "weight": 0.9},
    # 대출상품은 금리를 가진다
    {"source": "CONCEPT_LOAN_PRODUCT", "target": "CONCEPT_INTEREST_RATE",
     "relation_type": "includes",     "weight": 1.0},
    # 대출상품 신청 시 신청조건이 있다
    {"source": "CONCEPT_LOAN_PRODUCT", "target": "CONCEPT_APPLICATION_CONDITION",
     "relation_type": "has_condition", "weight": 1.0},
    # 대출상품 신청 시 서류가 필요하다
    {"source": "CONCEPT_LOAN_PRODUCT", "target": "CONCEPT_REQUIRED_DOCUMENT",
     "relation_type": "requires",      "weight": 0.8},
    # 대출상품은 정책/규정의 적용을 받는다
    {"source": "CONCEPT_LOAN_PRODUCT", "target": "CONCEPT_POLICY",
     "relation_type": "governed_by",   "weight": 0.7},

    # ── 개인신용대출 ──────────────────────────────────────────
    # 개인신용대출은 금리 정보를 포함한다
    {"source": "CONCEPT_PERSONAL_CREDIT_LOAN", "target": "CONCEPT_INTEREST_RATE",
     "relation_type": "includes",      "weight": 1.0},
    # 개인신용대출은 우대금리 조건을 포함한다
    {"source": "CONCEPT_PERSONAL_CREDIT_LOAN", "target": "CONCEPT_PREFERENTIAL_RATE",
     "relation_type": "includes",      "weight": 0.8},
    # 개인신용대출 신청 시 서류가 필요하다
    {"source": "CONCEPT_PERSONAL_CREDIT_LOAN", "target": "CONCEPT_REQUIRED_DOCUMENT",
     "relation_type": "requires",      "weight": 0.9},
    # 개인신용대출은 신청조건이 있다
    {"source": "CONCEPT_PERSONAL_CREDIT_LOAN", "target": "CONCEPT_APPLICATION_CONDITION",
     "relation_type": "has_condition", "weight": 0.9},
    # 개인신용대출은 정책/규정의 적용을 받는다
    {"source": "CONCEPT_PERSONAL_CREDIT_LOAN", "target": "CONCEPT_POLICY",
     "relation_type": "governed_by",   "weight": 0.7},

    # ── 금리 ──────────────────────────────────────────────────
    # 금리는 우대금리를 포함한다
    {"source": "CONCEPT_INTEREST_RATE", "target": "CONCEPT_PREFERENTIAL_RATE",
     "relation_type": "includes",      "weight": 0.9},

    # ── 정책/약관 ─────────────────────────────────────────────
    # 정책은 약관을 포함한다
    {"source": "CONCEPT_POLICY", "target": "CONCEPT_TERMS",
     "relation_type": "includes",      "weight": 0.9},

    # ── 신청조건 ──────────────────────────────────────────────
    # 신청조건 확인 시 서류 목록이 필요하다
    {"source": "CONCEPT_APPLICATION_CONDITION", "target": "CONCEPT_REQUIRED_DOCUMENT",
     "relation_type": "requires",      "weight": 0.8},

    # ── 고객 / 상담이력 ───────────────────────────────────────
    # 고객은 상담이력을 보유한다
    {"source": "CONCEPT_CUSTOMER", "target": "CONCEPT_COUNSELING_HISTORY",
     "relation_type": "has_record",    "weight": 0.7},
]


def seed_relations(db: Session) -> None:
    added = 0
    for r in RELATIONS:
        existing = (
            db.query(BusinessConceptRelation)
            .filter_by(
                source_concept_id=r["source"],
                target_concept_id=r["target"],
            )
            .first()
        )
        if existing is None:
            db.add(
                BusinessConceptRelation(
                    source_concept_id=r["source"],
                    target_concept_id=r["target"],
                    relation_type=r["relation_type"],
                    weight=r["weight"],
                    created_at=datetime.utcnow(),
                )
            )
            added += 1
        elif existing.relation_type != r["relation_type"] or existing.weight != r["weight"]:
            # relation_type·weight 변경 시 갱신
            existing.relation_type = r["relation_type"]
            existing.weight = r["weight"]

    db.commit()
    print(f"[relations_seed] {len(RELATIONS)} relations defined / {added} newly added.")
