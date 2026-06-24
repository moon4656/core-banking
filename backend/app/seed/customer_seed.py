from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge_model import CreditGradeRate, CustomerProfile

# 샘플 고객 4명 (신용등급 분포: 우량 2명, 일반 1명, 주의 1명)
CUSTOMERS = [
    {
        "customer_id": "CUSTOMER_001",
        "name": "이민준",
        "credit_grade": 2,
        "annual_income": 6000,
        "employment_type": "직장인",
    },
    {
        "customer_id": "CUSTOMER_002",
        "name": "김지영",
        "credit_grade": 5,
        "annual_income": 4000,
        "employment_type": "자영업자",
    },
    {
        "customer_id": "CUSTOMER_003",
        "name": "박철수",
        "credit_grade": 7,
        "annual_income": 3000,
        "employment_type": "프리랜서",
    },
    {
        "customer_id": "CUSTOMER_004",
        "name": "최수연",
        "credit_grade": 4,
        "annual_income": 5000,
        "employment_type": "직장인",
    },
]

# 신용등급(1~10) × 상품유형 금리표
# 등급 1~3: 우량 / 4~6: 일반 / 7~8: 주의 / 9~10: 위험
CREDIT_GRADE_RATES = [
    # ── 직장인 신용대출 ──────────────────────────────────
    {"product_type": "직장인 신용대출", "credit_grade": 1,  "min_rate": 3.0, "max_rate": 3.8},
    {"product_type": "직장인 신용대출", "credit_grade": 2,  "min_rate": 3.5, "max_rate": 4.5},
    {"product_type": "직장인 신용대출", "credit_grade": 3,  "min_rate": 4.0, "max_rate": 5.2},
    {"product_type": "직장인 신용대출", "credit_grade": 4,  "min_rate": 5.0, "max_rate": 6.5},
    {"product_type": "직장인 신용대출", "credit_grade": 5,  "min_rate": 6.0, "max_rate": 8.0},
    {"product_type": "직장인 신용대출", "credit_grade": 6,  "min_rate": 7.5, "max_rate": 9.5},
    {"product_type": "직장인 신용대출", "credit_grade": 7,  "min_rate": 9.0, "max_rate": 12.0},
    {"product_type": "직장인 신용대출", "credit_grade": 8,  "min_rate": 11.0, "max_rate": 14.0},
    {"product_type": "직장인 신용대출", "credit_grade": 9,  "min_rate": 13.0, "max_rate": 17.0},
    {"product_type": "직장인 신용대출", "credit_grade": 10, "min_rate": 16.0, "max_rate": 20.0},
    # ── 프리랜서·자영업자 신용대출 ───────────────────────
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 1,  "min_rate": 4.0, "max_rate": 5.0},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 2,  "min_rate": 4.5, "max_rate": 6.0},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 3,  "min_rate": 5.5, "max_rate": 7.0},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 4,  "min_rate": 6.5, "max_rate": 8.5},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 5,  "min_rate": 8.0, "max_rate": 10.5},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 6,  "min_rate": 9.5, "max_rate": 12.5},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 7,  "min_rate": 11.5, "max_rate": 15.0},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 8,  "min_rate": 14.0, "max_rate": 18.0},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 9,  "min_rate": 17.0, "max_rate": 20.0},
    {"product_type": "프리랜서·자영업자 신용대출", "credit_grade": 10, "min_rate": 19.0, "max_rate": 20.0},
    # ── 중금리 사잇돌2 대출 (4~8등급 대상) ─────────────
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 1,  "min_rate": 0.0,  "max_rate": 0.0},   # 해당없음
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 2,  "min_rate": 0.0,  "max_rate": 0.0},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 3,  "min_rate": 0.0,  "max_rate": 0.0},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 4,  "min_rate": 6.5,  "max_rate": 9.0},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 5,  "min_rate": 8.5,  "max_rate": 11.5},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 6,  "min_rate": 10.0, "max_rate": 13.5},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 7,  "min_rate": 12.0, "max_rate": 15.5},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 8,  "min_rate": 14.5, "max_rate": 17.5},
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 9,  "min_rate": 0.0,  "max_rate": 0.0},   # 해당없음
    {"product_type": "중금리 사잇돌2 대출", "credit_grade": 10, "min_rate": 0.0,  "max_rate": 0.0},
    # ── 주택담보대출 ─────────────────────────────────────
    {"product_type": "주택담보대출", "credit_grade": 1,  "min_rate": 2.8, "max_rate": 3.4},
    {"product_type": "주택담보대출", "credit_grade": 2,  "min_rate": 3.0, "max_rate": 3.7},
    {"product_type": "주택담보대출", "credit_grade": 3,  "min_rate": 3.2, "max_rate": 4.0},
    {"product_type": "주택담보대출", "credit_grade": 4,  "min_rate": 3.5, "max_rate": 4.5},
    {"product_type": "주택담보대출", "credit_grade": 5,  "min_rate": 4.0, "max_rate": 5.2},
    {"product_type": "주택담보대출", "credit_grade": 6,  "min_rate": 4.8, "max_rate": 6.2},
    {"product_type": "주택담보대출", "credit_grade": 7,  "min_rate": 5.8, "max_rate": 7.5},
    {"product_type": "주택담보대출", "credit_grade": 8,  "min_rate": 7.0, "max_rate": 9.0},
    {"product_type": "주택담보대출", "credit_grade": 9,  "min_rate": 8.5, "max_rate": 11.0},
    {"product_type": "주택담보대출", "credit_grade": 10, "min_rate": 10.0, "max_rate": 13.0},
]

_GRADE_LABEL = {
    1: "최우량", 2: "우량", 3: "양호",
    4: "보통", 5: "보통", 6: "보통",
    7: "주의", 8: "주의",
    9: "위험", 10: "위험",
}


def seed_customers(db: Session) -> None:
    for data in CUSTOMERS:
        existing = db.query(CustomerProfile).filter_by(customer_id=data["customer_id"]).first()
        if existing is None:
            db.add(
                CustomerProfile(
                    customer_id=data["customer_id"],
                    name=data["name"],
                    credit_grade=data["credit_grade"],
                    annual_income=data.get("annual_income"),
                    employment_type=data.get("employment_type"),
                    created_at=datetime.utcnow(),
                )
            )

    for data in CREDIT_GRADE_RATES:
        existing = (
            db.query(CreditGradeRate)
            .filter_by(product_type=data["product_type"], credit_grade=data["credit_grade"])
            .first()
        )
        if existing is None:
            db.add(
                CreditGradeRate(
                    product_type=data["product_type"],
                    credit_grade=data["credit_grade"],
                    min_rate=data["min_rate"],
                    max_rate=data["max_rate"],
                    created_at=datetime.utcnow(),
                )
            )

    db.commit()
    print(f"[customer_seed] {len(CUSTOMERS)} customers seeded.")
    print(f"[customer_seed] {len(CREDIT_GRADE_RATES)} credit grade rates seeded.")
