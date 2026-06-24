from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge_model import IntentTermSynonym

INTENT_SYNONYMS = [
    # ── 최저/최고 금리 (rate_agent 내부 사용) ─────────────────────────
    {"intent": "RATE_MIN", "term": "최저"},
    {"intent": "RATE_MIN", "term": "최소"},
    {"intent": "RATE_MIN", "term": "가장 낮은"},
    {"intent": "RATE_MIN", "term": "제일 낮은"},
    {"intent": "RATE_MIN", "term": "낮은"},
    {"intent": "RATE_MIN", "term": "최저금리"},
    {"intent": "RATE_MIN", "term": "최저 이율"},
    {"intent": "RATE_MIN", "term": "최저이율"},

    {"intent": "RATE_MAX", "term": "최고"},
    {"intent": "RATE_MAX", "term": "최대"},
    {"intent": "RATE_MAX", "term": "가장 높은"},
    {"intent": "RATE_MAX", "term": "제일 높은"},
    {"intent": "RATE_MAX", "term": "높은"},
    {"intent": "RATE_MAX", "term": "최고금리"},
    {"intent": "RATE_MAX", "term": "최고 이율"},
    {"intent": "RATE_MAX", "term": "최고이율"},

    # ── API 포커스 키워드 (leader.py _filter_results_by_question 사용) ─
    # MOCK_RATE_SIMULATION
    {"intent": "MOCK_RATE_SIMULATION", "term": "시뮬레이션"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "예측"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "계산"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "균등분할"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "원리금균등"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "원균등균상환"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "월납입"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "월 납입"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "상환하면"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "빌리면"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "얼마야"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "얼마인지"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "얼마나"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "납입금"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "상환금액"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "상환금"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "만원이면"},
    {"intent": "MOCK_RATE_SIMULATION", "term": "만원을"},

    # MOCK_PERSONALIZED_RATE_LOOKUP
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 금리"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "나의 금리"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 이자율"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 대출금리"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "등급별 금리"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용등급 금리"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "등급 금리"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 등급"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용등급은"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "등급인데"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "등급이면"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 신용등급"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용등급이"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용등급 조회"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용등급 어"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용도"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "나의 신용도"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 신용도"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용점수"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "내 신용점수"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "나의 신용점수"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용도를"},
    {"intent": "MOCK_PERSONALIZED_RATE_LOOKUP", "term": "신용도가"},

    # MOCK_RATE_LOOKUP
    {"intent": "MOCK_RATE_LOOKUP", "term": "금리"},
    {"intent": "MOCK_RATE_LOOKUP", "term": "이자율"},
    {"intent": "MOCK_RATE_LOOKUP", "term": "대출금리"},
    {"intent": "MOCK_RATE_LOOKUP", "term": "금리는"},
    {"intent": "MOCK_RATE_LOOKUP", "term": "금리가"},
    {"intent": "MOCK_RATE_LOOKUP", "term": "우대금리"},

    # MOCK_PRODUCT_LOOKUP
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "상품"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "상품목록"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "대출종류"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "어떤 대출"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "대출 상품"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "추천"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "추천해줘"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "맞는 대출"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "어떤게 좋"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "어떤 거 좋"},
    {"intent": "MOCK_PRODUCT_LOOKUP", "term": "뭐가 좋"},

    # MOCK_DOCUMENT_SEARCH
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "서류"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "구비서류"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "제출서류"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "필요서류"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "서류목록"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "어떤 서류"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "신청하려면"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "신청방법"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "신청절차"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "어떻게 신청"},
    {"intent": "MOCK_DOCUMENT_SEARCH", "term": "어떻게 해야"},

    # MOCK_ELIGIBILITY_CHECK
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "자격"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "신청조건"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "조건"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "신청가능"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "자격요건"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "누가 신청"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "신청하려면"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "신청방법"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "신청절차"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "어떻게 신청"},
    {"intent": "MOCK_ELIGIBILITY_CHECK", "term": "어떻게 해야"},

    # MOCK_POLICY_LOOKUP
    {"intent": "MOCK_POLICY_LOOKUP", "term": "정책"},
    {"intent": "MOCK_POLICY_LOOKUP", "term": "약관"},
    {"intent": "MOCK_POLICY_LOOKUP", "term": "규정"},
    {"intent": "MOCK_POLICY_LOOKUP", "term": "이용약관"},

    # MOCK_COUNSELING_HISTORY
    {"intent": "MOCK_COUNSELING_HISTORY", "term": "상담이력"},
    {"intent": "MOCK_COUNSELING_HISTORY", "term": "상담내역"},
    {"intent": "MOCK_COUNSELING_HISTORY", "term": "이전상담"},
    {"intent": "MOCK_COUNSELING_HISTORY", "term": "상담기록"},

    # MOCK_EXCHANGE_RATE_LOOKUP
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "달러환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "엔화환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "유로환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "달러"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "엔화"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "유로"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "위안"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "파운드"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "오늘환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "현재환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "USD"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "JPY"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "EUR"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "CNY"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "기준환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "매매기준율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "고시환율"},
    {"intent": "MOCK_EXCHANGE_RATE_LOOKUP", "term": "환시세"},

    # MOCK_CURRENCY_EXCHANGE_CALC
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전하면"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전하려면"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전금액"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "달러로 바꾸면"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "얼마나 받을 수 있"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전 계산"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전 수수료"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환전 우대"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "환율우대"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "외화 사기"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "달러 사기"},
    {"intent": "MOCK_CURRENCY_EXCHANGE_CALC", "term": "원화로 바꾸기"},

    # MOCK_FOREIGN_REMITTANCE
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "해외송금"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "송금"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "해외이체"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "외화송금"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "국제송금"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "송금 한도"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "송금 수수료"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "송금 방법"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "송금 시간"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "SWIFT"},
    {"intent": "MOCK_FOREIGN_REMITTANCE", "term": "스위프트"},

    # MOCK_FOREIGN_DEPOSIT_RATE
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화예금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "달러예금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화적금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화통장"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화 금리"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "달러 금리"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "달러 예금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화 예금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "달러 통장"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화 계좌"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화 정기예금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화 보통예금"},
    {"intent": "MOCK_FOREIGN_DEPOSIT_RATE", "term": "외화 예치"},

    # MOCK_NOTIFICATION_RULES
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "알림"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "알림규칙"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "알림 규칙"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "알림 설정"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "알림받"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "금리변동 알림"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "만기 알림"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "연체 알림"},
    {"intent": "MOCK_NOTIFICATION_RULES", "term": "푸시알림"},

    # MOCK_NOTIFICATION_SEND
    {"intent": "MOCK_NOTIFICATION_SEND", "term": "알림 발송"},
    {"intent": "MOCK_NOTIFICATION_SEND", "term": "알림 보내줘"},
    {"intent": "MOCK_NOTIFICATION_SEND", "term": "알림 보내"},
    {"intent": "MOCK_NOTIFICATION_SEND", "term": "알림발송"},
]


def run(db: Session) -> None:
    existing = {(r.intent, r.term) for r in db.query(IntentTermSynonym).all()}
    new_rows = [
        IntentTermSynonym(
            intent=row["intent"],
            term=row["term"],
            language="ko",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        for row in INTENT_SYNONYMS
        if (row["intent"], row["term"]) not in existing
    ]
    if new_rows:
        db.bulk_save_objects(new_rows)
        db.commit()
        print(f"[intent_synonyms_seed] {len(new_rows)}개 용어 등록 완료")
    else:
        print("[intent_synonyms_seed] 이미 모두 등록되어 있음")
