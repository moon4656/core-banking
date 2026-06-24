from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge_model import BusinessConcept, BusinessTermAlias

CONCEPTS = [
    {
        "concept_id": "CONCEPT_CUSTOMER",
        "name": "고객 정보",
        "description": "대출 신청 고객의 기본 정보 및 신용 정보",
        "domain": "customer",
        "aliases": ["고객", "customer", "신청인"],
    },
    {
        "concept_id": "CONCEPT_LOAN_PRODUCT",
        "name": "대출 상품",
        "description": "은행이 제공하는 대출 상품 목록 및 조건",
        "domain": "loan",
        "aliases": ["대출상품", "loan product", "여신상품", "마이너스통장", "한도대출", "마통", "신용한도", "대출종류", "대출상품목록"],
    },
    {
        "concept_id": "CONCEPT_PERSONAL_CREDIT_LOAN",
        "name": "개인 신용대출",
        "description": "개인 신용도 기반 무담보 대출 상품",
        "domain": "loan",
        "aliases": ["신용대출", "personal loan", "개인대출", "무담보대출", "신용론", "직장인대출", "소액대출", "개인신용대출"],
    },
    {
        "concept_id": "CONCEPT_INTEREST_RATE",
        "name": "금리",
        "description": "대출 상품별 적용 금리 정보",
        "domain": "rate",
        "aliases": ["금리", "interest rate", "이자율", "대출금리", "월납입금", "월 납입금", "상환금", "월 상환금", "원리금균등상환", "균등분할상환", "균등상환", "원리금", "납입금", "빌리면", "얼마야", "계산", "시뮬레이션", "상환금액"],
    },
    {
        "concept_id": "CONCEPT_PREFERENTIAL_RATE",
        "name": "우대금리",
        "description": "특정 조건 충족 시 적용되는 금리 할인 혜택",
        "domain": "rate",
        "aliases": ["우대금리", "preferential rate", "금리 우대", "할인금리"],
    },
    {
        "concept_id": "CONCEPT_REQUIRED_DOCUMENT",
        "name": "필요서류",
        "description": "대출 신청 시 제출해야 하는 서류 목록",
        "domain": "document",
        "aliases": ["필요서류", "required document", "구비서류", "제출서류", "관련서류", "서류", "서류목록", "제출서류목록", "신청서류"],
    },
    {
        "concept_id": "CONCEPT_POLICY",
        "name": "정책/규정",
        "description": "대출 관련 내부 정책 및 규정",
        "domain": "policy",
        "aliases": ["정책", "규정", "policy", "여신정책"],
    },
    {
        "concept_id": "CONCEPT_TERMS",
        "name": "약관",
        "description": "대출 약관 및 계약 조건",
        "domain": "policy",
        "aliases": ["약관", "terms", "계약조건", "이용약관"],
    },
    {
        "concept_id": "CONCEPT_COUNSELING_HISTORY",
        "name": "상담이력",
        "description": "고객 상담 이력 및 문의 내역",
        "domain": "counseling",
        "aliases": ["상담이력", "counseling history", "상담내역", "문의이력", "상담기록", "이전상담", "문의내역"],
    },
    {
        "concept_id": "CONCEPT_APPLICATION_CONDITION",
        "name": "신청조건",
        "description": "대출 신청 자격 요건 및 조건",
        "domain": "loan",
        "aliases": ["신청조건", "application condition", "자격요건", "신청자격", "대출조건", "가입조건", "신청가능", "대상자", "신청하려면", "신청방법", "신청절차", "어떻게 신청"],
    },
    # ── 외화 거래 ──────────────────────────────────────────────────
    {
        "concept_id": "CONCEPT_EXCHANGE_RATE",
        "name": "환율",
        "description": "외화 환율 정보 및 변동 현황",
        "domain": "forex",
        "aliases": ["환율", "exchange rate", "달러", "엔화", "유로", "위안", "외환", "USD", "JPY", "EUR", "CNY", "기준환율", "매매기준율", "고시환율", "환시세"],
    },
    {
        "concept_id": "CONCEPT_FOREIGN_REMITTANCE",
        "name": "해외송금",
        "description": "해외로 외화를 송금하는 서비스",
        "domain": "forex",
        "aliases": ["해외송금", "foreign remittance", "송금", "해외이체", "외화송금", "international transfer", "remittance", "국제송금", "송금 한도", "송금 수수료", "송금 방법", "송금 시간", "SWIFT", "스위프트"],
    },
    {
        "concept_id": "CONCEPT_CURRENCY_EXCHANGE",
        "name": "외화환전",
        "description": "원화를 외화로 또는 외화를 원화로 환전하는 서비스",
        "domain": "forex",
        "aliases": ["환전", "currency exchange", "외화환전", "달러환전", "엔화환전", "환전신청", "환전금액", "환전하면", "환전 수수료", "환전 우대", "환율우대", "외화 사기", "달러 사기", "원화로 바꾸기"],
    },
    {
        "concept_id": "CONCEPT_FOREIGN_DEPOSIT",
        "name": "외화예금",
        "description": "외화로 예금하는 상품 및 금리 정보",
        "domain": "forex",
        "aliases": ["외화예금", "외화 예금", "foreign deposit", "외화적금", "달러예금", "달러 예금", "외화통장", "외화저축", "달러 통장", "외화 계좌", "외화 정기예금", "외화 보통예금", "외화 예치"],
    },
    # ── 알림 ──────────────────────────────────────────────────────
    {
        "concept_id": "CONCEPT_NOTIFICATION",
        "name": "알림/통지",
        "description": "대출 금리변동, 만기, 연체, 한도소진 등 고객 알림 서비스",
        "domain": "notification",
        "aliases": ["알림", "notification", "통지", "푸시알림", "문자알림", "SMS", "push", "알림설정", "알림규칙", "알림받고싶어", "알림보내"],
    },
    {
        "concept_id": "CONCEPT_LOAN_STATUS",
        "name": "대출현황",
        "description": "현재 대출 잔액, 만기일, 연체 여부 등 대출 상태 정보",
        "domain": "loan",
        "aliases": ["대출현황", "loan status", "대출잔액", "잔액", "만기", "만기일", "연체", "상환현황", "내대출", "대출상태"],
    },
]


def seed_concepts(db: Session) -> None:
    for data in CONCEPTS:
        existing = db.query(BusinessConcept).filter_by(concept_id=data["concept_id"]).first()
        if existing is None:
            concept = BusinessConcept(
                concept_id=data["concept_id"],
                name=data["name"],
                description=data["description"],
                domain=data["domain"],
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(concept)
            db.flush()

        for alias_text in data.get("aliases", []):
            alias_exists = (
                db.query(BusinessTermAlias)
                .filter_by(concept_id=data["concept_id"], alias=alias_text)
                .first()
            )
            if alias_exists is None:
                db.add(
                    BusinessTermAlias(
                        concept_id=data["concept_id"],
                        alias=alias_text,
                        language="ko",
                        created_at=datetime.utcnow(),
                    )
                )

    db.commit()
    print(f"[concepts_seed] {len(CONCEPTS)} concepts seeded.")
