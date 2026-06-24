"""
Mock API — 은행 내부 시스템 대체용

[제공 엔드포인트]
  GET /health                          헬스 체크
  GET /products                        대출 상품 목록
  GET /products/{product_id}           상품 상세
  GET /rates                           금리 목록
  GET /rates/simulation                월 상환금 시뮬레이션
  GET /rates/personalized              신용등급별 맞춤 금리
  GET /policies                        정책/약관 목록
  GET /documents/search                필요서류 검색
  GET /customers/credit                고객 신용 정보 (Mock)
  GET /applications/eligibility        대출 신청 자격 확인
  GET /counseling/history              상담 이력
  GET /branches                        영업점 정보
  GET /forex/rates                     외환 환율 조회
  GET /forex/exchange-calc             외화 환전 계산
  GET /forex/remittance                해외송금 안내
  GET /forex/deposit-rates             외화예금 금리
  GET /notifications/rules             알림 규칙 조회
  POST /notifications/send             알림 발송
"""

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(
    title="AI Agent Mock API",
    description="은행 내부 시스템 대체용 Mock API",
    version="0.3.0",
)

# ─────────────────────────────────────────────
# 대출 상품 데이터
# ─────────────────────────────────────────────
_PRODUCTS = [
    {
        "product_id": "P001",
        "name": "직장인 신용대출",
        "product_type": "신용대출",
        "target_customer": "재직자 (근무기간 3개월 이상)",
        "max_amount": 100_000_000,
        "min_amount": 1_000_000,
        "min_rate": 4.5,
        "max_rate": 9.8,
        "min_term_months": 12,
        "max_term_months": 60,
        "repayment_method": ["원리금균등상환", "만기일시상환"],
        "features": [
            "신용점수 650점 이상 신청 가능",
            "최대 1억원까지 한도 제공",
            "급여이체 시 우대금리 최대 0.5% 추가",
            "비대면 100% 온라인 신청 가능",
        ],
        "is_active": True,
    },
    {
        "product_id": "P002",
        "name": "프리랜서·자영업자 신용대출",
        "product_type": "신용대출",
        "target_customer": "사업자등록증 보유 자영업자 또는 프리랜서",
        "max_amount": 50_000_000,
        "min_amount": 1_000_000,
        "min_rate": 5.8,
        "max_rate": 13.5,
        "min_term_months": 12,
        "max_term_months": 36,
        "repayment_method": ["원리금균등상환"],
        "features": [
            "사업 영위 1년 이상",
            "직전연도 매출 3천만원 이상",
            "부동산 담보 없이 신용으로만 가능",
            "세금 완납 확인 필수",
        ],
        "is_active": True,
    },
    {
        "product_id": "P003",
        "name": "중금리 사잇돌2 대출",
        "product_type": "중금리대출",
        "target_customer": "신용점수 600~839점 중·저신용자",
        "max_amount": 20_000_000,
        "min_amount": 500_000,
        "min_rate": 6.5,
        "max_rate": 15.9,
        "min_term_months": 12,
        "max_term_months": 60,
        "repayment_method": ["원리금균등상환"],
        "features": [
            "SGI서울보증 보증서 발급 대출",
            "기존 고금리 대출 대환 가능",
            "대부업 이용자도 신청 가능",
            "정부 지원 중금리 상품",
        ],
        "is_active": True,
    },
    {
        "product_id": "P004",
        "name": "버팀목 전세자금대출",
        "product_type": "전세대출",
        "target_customer": "무주택 세대주 (부부합산 연소득 5천만원 이하)",
        "max_amount": 120_000_000,
        "min_amount": 1_000_000,
        "min_rate": 2.1,
        "max_rate": 2.9,
        "min_term_months": 12,
        "max_term_months": 24,
        "repayment_method": ["만기일시상환"],
        "features": [
            "주택도시기금 지원 저금리 상품",
            "수도권 최대 1.2억, 지방 최대 8천만원",
            "청년(만 19~34세) 우대금리 0.2% 추가",
            "신혼부부 우대금리 0.2% 추가",
            "갱신 시 2년 연장 가능",
        ],
        "is_active": True,
    },
    {
        "product_id": "P005",
        "name": "주택담보대출 (변동금리)",
        "product_type": "담보대출",
        "target_customer": "주택 보유자 (LTV 70% 이내)",
        "max_amount": 500_000_000,
        "min_amount": 10_000_000,
        "min_rate": 3.6,
        "max_rate": 5.2,
        "min_term_months": 12,
        "max_term_months": 360,
        "repayment_method": ["원리금균등상환", "원금균등상환", "만기일시상환"],
        "features": [
            "COFIX 연동 6개월 변동금리",
            "LTV 70% / DTI 60% / DSR 40% 적용",
            "주택 감정평가 비용 은행 부담",
            "중도상환수수료 3년 내 1.2%",
        ],
        "is_active": True,
    },
    {
        "product_id": "P006",
        "name": "주택담보대출 (고정금리)",
        "product_type": "담보대출",
        "target_customer": "주택 보유자 (LTV 70% 이내)",
        "max_amount": 500_000_000,
        "min_amount": 10_000_000,
        "min_rate": 3.9,
        "max_rate": 5.5,
        "min_term_months": 12,
        "max_term_months": 360,
        "repayment_method": ["원리금균등상환", "원금균등상환"],
        "features": [
            "5년 고정 후 변동 전환 선택 가능",
            "금리 인상기 리스크 헤지 가능",
            "LTV 70% / DTI 60% / DSR 40% 적용",
            "특례보금자리론 연계 상품",
        ],
        "is_active": True,
    },
    {
        "product_id": "P007",
        "name": "마이너스통장 (한도대출)",
        "product_type": "한도대출",
        "target_customer": "당행 급여 수령 직장인 (근무기간 1년 이상)",
        "max_amount": 30_000_000,
        "min_amount": 1_000_000,
        "min_rate": 4.8,
        "max_rate": 8.9,
        "min_term_months": 12,
        "max_term_months": 12,
        "repayment_method": ["한도 내 자유 입출금"],
        "features": [
            "필요할 때만 인출, 인출액에만 이자 발생",
            "1년 단위 자동 연장",
            "공과금 자동납부 설정 시 0.1% 우대",
            "당행 급여이체 고객 전용",
        ],
        "is_active": True,
    },
    {
        "product_id": "P008",
        "name": "자동차담보대출",
        "product_type": "담보대출",
        "target_customer": "자동차 소유자 (차량기준가액 500만원 이상)",
        "max_amount": 50_000_000,
        "min_amount": 1_000_000,
        "min_rate": 5.5,
        "max_rate": 11.5,
        "min_term_months": 12,
        "max_term_months": 60,
        "repayment_method": ["원리금균등상환"],
        "features": [
            "차량 기준가액 최대 90%까지 대출",
            "당일 대출 실행 가능",
            "자동차 등록원부 담보 설정",
            "5년 이내 차량만 가능",
        ],
        "is_active": True,
    },
]

# ─────────────────────────────────────────────
# 금리 데이터
# ─────────────────────────────────────────────
_RATES = {
    "P001": {
        "product_id": "P001",
        "product_name": "직장인 신용대출",
        "base_rate": 4.5,
        "base_rate_standard": "은행채 1년물 (3.8%) + 가산금리 0.7%",
        "rate_type": "변동금리",
        "rate_change_cycle": "6개월",
        "preferential_conditions": [
            {"condition": "급여이체 고객", "discount": 0.3, "description": "당행 주거래 급여이체 등록 시"},
            {"condition": "자동이체 3건 이상", "discount": 0.1, "description": "공과금 등 자동이체 3건 이상 등록"},
            {"condition": "신용카드 월 30만원 이상 사용", "discount": 0.1, "description": "당행 신용카드 전월 실적 기준"},
            {"condition": "청약저축 보유", "discount": 0.1, "description": "당행 주택청약종합저축 보유 고객"},
        ],
        "max_preferential": 0.5,
        "min_final_rate": 4.0,
        "max_final_rate": 9.8,
        "overdue_rate": 15.0,
        "early_repayment_fee": [
            {"within_months": 12, "fee_rate": 1.2},
            {"within_months": 24, "fee_rate": 0.8},
            {"within_months": 36, "fee_rate": 0.4},
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
    "P002": {
        "product_id": "P002",
        "product_name": "프리랜서·자영업자 신용대출",
        "base_rate": 7.2,
        "base_rate_standard": "은행채 1년물 (3.8%) + 가산금리 3.4%",
        "rate_type": "고정금리",
        "rate_change_cycle": "없음 (고정)",
        "preferential_conditions": [
            {"condition": "당행 사업자통장 주거래", "discount": 0.3, "description": "월 거래금액 500만원 이상"},
            {"condition": "세금 완납 확인서 제출", "discount": 0.2, "description": "최근 1년 세금 완납"},
            {"condition": "매출 전년비 10% 이상 증가", "discount": 0.2, "description": "부가세 신고 기준"},
        ],
        "max_preferential": 0.5,
        "min_final_rate": 5.8,
        "max_final_rate": 13.5,
        "overdue_rate": 18.0,
        "early_repayment_fee": [
            {"within_months": 12, "fee_rate": 1.5},
            {"within_months": 24, "fee_rate": 1.0},
            {"within_months": 36, "fee_rate": 0.5},
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
    "P003": {
        "product_id": "P003",
        "product_name": "중금리 사잇돌2 대출",
        "base_rate": 10.5,
        "base_rate_standard": "SGI보증료 포함 운영비용 반영",
        "rate_type": "고정금리",
        "rate_change_cycle": "없음 (고정)",
        "preferential_conditions": [
            {"condition": "고금리 대출 대환 목적", "discount": 0.5, "description": "20% 초과 고금리 대출 상환 목적"},
        ],
        "max_preferential": 0.5,
        "min_final_rate": 6.5,
        "max_final_rate": 15.9,
        "overdue_rate": 20.0,
        "early_repayment_fee": [
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
    "P004": {
        "product_id": "P004",
        "product_name": "버팀목 전세자금대출",
        "base_rate": 2.5,
        "base_rate_standard": "주택도시기금 정책금리",
        "rate_type": "고정금리",
        "rate_change_cycle": "없음 (기금 고시금리)",
        "preferential_conditions": [
            {"condition": "청년 (만 19~34세)", "discount": 0.2, "description": "대출 신청일 기준 만 34세 이하"},
            {"condition": "신혼부부 (혼인 7년 이내)", "discount": 0.2, "description": "혼인관계증명서 제출"},
            {"condition": "다자녀 가구 (자녀 3명 이상)", "discount": 0.5, "description": "주민등록등본 기준"},
            {"condition": "장애인 가구", "discount": 0.2, "description": "장애인 증명서 제출"},
        ],
        "max_preferential": 0.7,
        "min_final_rate": 1.8,
        "max_final_rate": 2.9,
        "overdue_rate": 8.0,
        "early_repayment_fee": [
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
    "P005": {
        "product_id": "P005",
        "product_name": "주택담보대출 (변동금리)",
        "base_rate": 4.2,
        "base_rate_standard": "COFIX 6개월물 (3.5%) + 가산금리 0.7%",
        "rate_type": "변동금리",
        "rate_change_cycle": "6개월 (1월·7월 기준)",
        "preferential_conditions": [
            {"condition": "급여이체 고객", "discount": 0.2, "description": "당행 급여이체 등록"},
            {"condition": "주택화재보험 당행 가입", "discount": 0.1, "description": "당행 제휴 화재보험 가입"},
            {"condition": "인터넷·모바일 신청", "discount": 0.1, "description": "비대면 채널 신청 시"},
            {"condition": "LTV 60% 이하", "discount": 0.2, "description": "담보인정비율 60% 이하"},
        ],
        "max_preferential": 0.5,
        "min_final_rate": 3.6,
        "max_final_rate": 5.2,
        "overdue_rate": 15.0,
        "ltv_limit": 70,
        "dti_limit": 60,
        "dsr_limit": 40,
        "early_repayment_fee": [
            {"within_months": 36, "fee_rate": 1.2},
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
    "P006": {
        "product_id": "P006",
        "product_name": "주택담보대출 (고정금리)",
        "base_rate": 4.5,
        "base_rate_standard": "금융채 5년물 (4.0%) + 가산금리 0.5%",
        "rate_type": "혼합금리 (5년고정 후 변동)",
        "rate_change_cycle": "5년 고정 후 6개월 변동",
        "preferential_conditions": [
            {"condition": "급여이체 고객", "discount": 0.2, "description": "당행 급여이체 등록"},
            {"condition": "주택화재보험 당행 가입", "discount": 0.1, "description": "당행 제휴 화재보험 가입"},
            {"condition": "LTV 60% 이하", "discount": 0.2, "description": "담보인정비율 60% 이하"},
        ],
        "max_preferential": 0.4,
        "min_final_rate": 3.9,
        "max_final_rate": 5.5,
        "overdue_rate": 15.0,
        "ltv_limit": 70,
        "dti_limit": 60,
        "dsr_limit": 40,
        "early_repayment_fee": [
            {"within_months": 36, "fee_rate": 1.2},
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
    "P007": {
        "product_id": "P007",
        "product_name": "마이너스통장",
        "base_rate": 6.5,
        "base_rate_standard": "CD금리 (3.5%) + 가산금리 3.0%",
        "rate_type": "변동금리",
        "rate_change_cycle": "3개월",
        "preferential_conditions": [
            {"condition": "급여이체 고객", "discount": 0.5, "description": "당행 급여이체 등록"},
            {"condition": "공과금 자동납부 3건 이상", "discount": 0.1, "description": "통신·전기·보험 등"},
            {"condition": "당행 신용카드 월 50만원 이상", "discount": 0.1, "description": "전월 실적 기준"},
        ],
        "max_preferential": 0.7,
        "min_final_rate": 4.8,
        "max_final_rate": 8.9,
        "overdue_rate": 15.0,
        "early_repayment_fee": [],
        "updated_at": "2026-06-01",
    },
    "P008": {
        "product_id": "P008",
        "product_name": "자동차담보대출",
        "base_rate": 7.5,
        "base_rate_standard": "CD금리 (3.5%) + 가산금리 4.0%",
        "rate_type": "고정금리",
        "rate_change_cycle": "없음 (고정)",
        "preferential_conditions": [
            {"condition": "당행 주거래 고객 (1년 이상)", "discount": 0.3, "description": "당행 계좌 주거래 1년 이상"},
            {"condition": "신용점수 800점 이상", "discount": 0.5, "description": "CB사 신용점수 800점 이상"},
        ],
        "max_preferential": 0.8,
        "min_final_rate": 5.5,
        "max_final_rate": 11.5,
        "overdue_rate": 20.0,
        "early_repayment_fee": [
            {"within_months": 12, "fee_rate": 1.0},
            {"within_months": 999, "fee_rate": 0.0},
        ],
        "updated_at": "2026-06-01",
    },
}

# ─────────────────────────────────────────────
# 정책/약관 데이터
# ─────────────────────────────────────────────
_POLICIES = [
    # ── 심사 기준 ──
    {
        "policy_id": "POL001",
        "policy_type": "심사기준",
        "title": "개인신용대출 기본 심사 기준",
        "content": "신용점수 650점 이상, 연소득 3천만원 이상, 현 직장 근무 3개월 이상",
        "detail": {
            "min_credit_score": 650,
            "min_annual_income": 30_000_000,
            "min_employment_months": 3,
            "excluded_occupations": ["일용직", "단기계약직(3개월 미만)"],
            "excluded_credit_status": ["개인회생", "파산", "신용불량 3개월 이내"],
        },
        "effective_date": "2026-01-01",
    },
    {
        "policy_id": "POL002",
        "policy_type": "심사기준",
        "title": "주택담보대출 LTV/DTI/DSR 기준",
        "content": "투기지역 LTV 40%, 규제지역 LTV 60%, 일반지역 LTV 70%. DTI 60%, DSR 40%",
        "detail": {
            "ltv_speculative_area": 40,
            "ltv_regulated_area": 60,
            "ltv_general_area": 70,
            "dti_limit": 60,
            "dsr_limit": 40,
            "dsr_exception": "서민금융상품(사잇돌 등)은 DSR 적용 제외",
        },
        "effective_date": "2026-01-01",
    },
    {
        "policy_id": "POL003",
        "policy_type": "심사기준",
        "title": "전세자금대출 자격 요건",
        "content": "무주택 세대주, 전세금액 수도권 4억 이하/지방 2억 이하, 부부합산 연소득 5천만원 이하",
        "detail": {
            "household_requirement": "무주택 세대주",
            "max_jeonse_price_metro": 400_000_000,
            "max_jeonse_price_other": 200_000_000,
            "max_household_income": 50_000_000,
            "max_loan_ratio": 80,
        },
        "effective_date": "2026-01-01",
    },
    # ── 우대금리 ──
    {
        "policy_id": "POL010",
        "policy_type": "우대금리",
        "title": "우대금리 적용 기준 및 한도",
        "content": "급여이체 0.3%, 자동이체 3건 0.1%, 카드실적 30만원 0.1%, 청약저축 0.1%. 최대 0.5% 중복 적용",
        "detail": {
            "preferential_items": [
                {"item": "급여이체", "rate": 0.3, "condition": "당행 급여이체 등록 유지"},
                {"item": "자동이체 3건 이상", "rate": 0.1, "condition": "공과금 포함 3건 이상"},
                {"item": "신용카드 월 30만원 이상", "rate": 0.1, "condition": "당행 카드 전월 실적"},
                {"item": "청약저축 보유", "rate": 0.1, "condition": "당행 주택청약종합저축"},
            ],
            "max_total_discount": 0.5,
            "review_cycle": "6개월마다 재검토",
            "cancellation_condition": "조건 미충족 시 다음 이자 지급일부터 원래 금리 적용",
        },
        "effective_date": "2026-01-01",
    },
    # ── 중도상환 ──
    {
        "policy_id": "POL020",
        "policy_type": "중도상환수수료",
        "title": "중도상환수수료 기준",
        "content": "실행 후 3년 이내 1.2%, 2년 이내 0.8%, 1년 이내 0.4%, 3년 초과 무료",
        "detail": {
            "fee_structure": [
                {"period": "실행 후 1년 이내", "fee_rate": 1.2, "formula": "잔여원금 × 1.2% × 잔여일수/대출기간일수"},
                {"period": "1년 초과 ~ 2년 이내", "fee_rate": 0.8, "formula": "잔여원금 × 0.8% × 잔여일수/대출기간일수"},
                {"period": "2년 초과 ~ 3년 이내", "fee_rate": 0.4, "formula": "잔여원금 × 0.4% × 잔여일수/대출기간일수"},
                {"period": "3년 초과", "fee_rate": 0.0, "formula": "면제"},
            ],
            "exempt_cases": [
                "일시적 2주택자의 기존 주택 처분 시",
                "연간 원금의 10% 이내 부분 상환",
                "사잇돌 대출 전액",
                "버팀목 전세자금대출 전액",
            ],
        },
        "effective_date": "2026-01-01",
    },
    # ── 약관 ──
    {
        "policy_id": "POL030",
        "policy_type": "약관",
        "title": "여신거래 기본 약관",
        "content": "기한이익 상실 사유: 연체 3개월 이상, 파산·회생 신청, 강제집행 개시. 기한이익 상실 시 전액 즉시 상환 요구 가능",
        "detail": {
            "acceleration_clauses": [
                "원금 또는 이자 2회 이상 연속 연체",
                "개인회생·파산 신청",
                "강제집행, 가압류, 경매 신청",
                "허위 서류 제출 적발",
                "담보물 가치 현저히 감소 (담보대출)",
            ],
            "overdue_interest_rate": "약정금리 + 3% (최고 연 20%)",
            "collection_procedure": "연체 → 독촉 → 신용정보원 등록 → 법적 조치",
        },
        "effective_date": "2026-01-01",
    },
    # ── 연체 정책 ──
    {
        "policy_id": "POL040",
        "policy_type": "연체정책",
        "title": "연체 처리 및 신용정보 등록 기준",
        "content": "연체 30일 이상 시 신용정보원 등록. 연체 90일 이상 시 대출 기한이익 상실 및 전액 청구",
        "detail": {
            "credit_bureau_registration": {
                "trigger": "연체 30일 이상",
                "report_to": "한국신용정보원 (NICE, KCB)",
                "deletion": "완납 후 5년간 보존 후 삭제",
            },
            "stages": [
                {"days": "1~29일", "action": "문자/앱 알림, 연체이자 발생"},
                {"days": "30일", "action": "신용정보원 연체 등록"},
                {"days": "90일", "action": "기한이익 상실, 전액 청구"},
                {"days": "180일", "action": "부실채권 분류, 채권 매각 검토"},
            ],
        },
        "effective_date": "2026-01-01",
    },
    # ── 대출 한도 정책 ──
    {
        "policy_id": "POL050",
        "policy_type": "한도정책",
        "title": "총부채원리금상환비율 (DSR) 산정 기준",
        "content": "모든 금융기관 대출의 연간 원리금 합계가 연소득의 40% 이내. 2억 초과 대출은 엄격 적용",
        "detail": {
            "dsr_standard": "연간 원리금 상환액 / 연소득 × 100 ≤ 40%",
            "included_debts": ["주택담보대출", "신용대출", "카드론", "할부금융", "학자금대출"],
            "excluded_debts": ["전세자금대출(임차보증금반환목적)", "사잇돌대출", "생활안정자금"],
            "strict_application": "대출 합계 2억 초과 시 은행권 DSR 40% 엄격 적용",
        },
        "effective_date": "2026-01-01",
    },
]

# ─────────────────────────────────────────────
# 필요서류 데이터
# ─────────────────────────────────────────────
_DOCUMENTS = [
    # ── 공통 필수 서류 ──
    {
        "doc_id": "DOC001",
        "category": "공통필수",
        "name": "신분증",
        "applicable_products": ["ALL"],
        "description": "주민등록증 또는 운전면허증 (외국인: 외국인등록증)",
        "validity": "없음 (유효한 신분증)",
        "notes": "만료된 신분증 불가, 촬영본 불가",
    },
    {
        "doc_id": "DOC002",
        "category": "소득증빙",
        "name": "근로소득 확인 서류 (직장인)",
        "applicable_products": ["P001", "P005", "P006", "P007"],
        "description": "근로소득원천징수영수증(전년도) + 재직증명서 또는 건강보험료 납부확인서",
        "validity": "발급일로부터 3개월 이내",
        "notes": "4대보험 가입 확인 필수. 입사 1년 미만 시 재직증명서로 대체 가능",
    },
    {
        "doc_id": "DOC003",
        "category": "소득증빙",
        "name": "사업소득 확인 서류 (자영업자)",
        "applicable_products": ["P002"],
        "description": "사업자등록증 + 전년도 종합소득세 신고서(또는 부가세 신고서) + 사업장 임대차계약서",
        "validity": "사업자등록증 최신본, 신고서 전년도분",
        "notes": "사업 영위 1년 미만 시 대출 불가. 면세 사업자는 부가세 신고서 불필요",
    },
    {
        "doc_id": "DOC004",
        "category": "소득증빙",
        "name": "건강보험료 납부확인서",
        "applicable_products": ["P001", "P002", "P003"],
        "description": "국민건강보험공단 발급. 직장가입자/지역가입자 구분 확인",
        "validity": "발급일로부터 3개월 이내",
        "notes": "국민건강보험공단 홈페이지 또는 정부24에서 무료 발급 가능",
    },
    # ── 전세대출 전용 ──
    {
        "doc_id": "DOC010",
        "category": "전세대출",
        "name": "임대차계약서 (전세계약서)",
        "applicable_products": ["P004"],
        "description": "임대인·임차인 서명, 확정일자 받은 임대차계약서 원본",
        "validity": "계약기간 유효 중",
        "notes": "확정일자 미부여 시 대출 실행 전 부여 필수. 전입신고 완료 확인",
    },
    {
        "doc_id": "DOC011",
        "category": "전세대출",
        "name": "주민등록등본 (무주택 확인용)",
        "applicable_products": ["P004"],
        "description": "세대원 전체 포함 주민등록등본",
        "validity": "발급일로부터 1개월 이내",
        "notes": "세대원 중 주택 소유자 있으면 버팀목 대출 불가",
    },
    {
        "doc_id": "DOC012",
        "category": "전세대출",
        "name": "등기부등본 (전세 목적물)",
        "applicable_products": ["P004"],
        "description": "대출 목적 주택의 건물 등기부등본 (갑구·을구 포함)",
        "validity": "발급일로부터 1개월 이내",
        "notes": "근저당권 과다 설정 시 대출 불가. 선순위 채권 합계 전세금의 80% 초과 불가",
    },
    # ── 담보대출 전용 ──
    {
        "doc_id": "DOC020",
        "category": "담보대출",
        "name": "부동산 등기부등본",
        "applicable_products": ["P005", "P006"],
        "description": "담보 부동산의 건물·토지 등기부등본 각 1통",
        "validity": "발급일로부터 1개월 이내",
        "notes": "권리관계 이상 없어야 함. 가압류·압류·경매 진행 중인 경우 대출 불가",
    },
    {
        "doc_id": "DOC021",
        "category": "담보대출",
        "name": "부동산 감정평가서",
        "applicable_products": ["P005", "P006"],
        "description": "은행 지정 감정평가법인의 감정평가서",
        "validity": "6개월 이내",
        "notes": "감정평가 비용 은행 부담. 은행 지정 평가법인 이용 필수",
    },
    # ── 자동차 담보 ──
    {
        "doc_id": "DOC030",
        "category": "자동차담보",
        "name": "자동차등록증",
        "applicable_products": ["P008"],
        "description": "말소이력 없는 유효한 자동차등록증",
        "validity": "최신본",
        "notes": "리스·할부 잔금 있는 차량은 별도 확인. 5년 이내 제조 차량만 가능",
    },
    {
        "doc_id": "DOC031",
        "category": "자동차담보",
        "name": "자동차 보험 가입 확인서",
        "applicable_products": ["P008"],
        "description": "대인·대물 보험 가입 확인. 보험료 완납 확인",
        "validity": "보험 유효기간 내",
        "notes": "담보 대출 실행 후 보험 해지 시 즉시 통보 의무",
    },
    # ── 우대금리 입증 서류 ──
    {
        "doc_id": "DOC040",
        "category": "우대금리",
        "name": "급여이체 확인서류",
        "applicable_products": ["P001", "P005", "P006", "P007"],
        "description": "당행 급여이체 3개월 이상 내역 또는 급여이체 신청서",
        "validity": "신청 시점 기준",
        "notes": "급여이체 신규 신청 시 대출 실행 후 1회 이체 시점부터 우대 적용",
    },
    # ── 청년·신혼부부 우대 ──
    {
        "doc_id": "DOC050",
        "category": "우대자격",
        "name": "혼인관계증명서 (신혼부부 우대)",
        "applicable_products": ["P004"],
        "description": "혼인 7년 이내 신혼부부 우대금리 적용을 위한 혼인관계증명서",
        "validity": "발급일로부터 3개월 이내",
        "notes": "재혼도 적용 가능. 혼인일로부터 7년 이내여야 함",
    },
]

# ─────────────────────────────────────────────
# Mock 고객 신용 정보
# ─────────────────────────────────────────────
_MOCK_CUSTOMERS = {
    "C001": {
        "customer_id": "C001",
        "name": "김*수",
        "credit_score": 782,
        "credit_grade": "2등급",
        "annual_income": 52_000_000,
        "employment_type": "정규직",
        "employment_months": 48,
        "existing_loans": [
            {"type": "신용대출", "balance": 10_000_000, "monthly_payment": 210_000},
        ],
        "total_debt_ratio": 18.5,
        "dsr": 14.2,
        "overdue_history": False,
        "evaluated_at": "2026-06-01",
    },
    "C002": {
        "customer_id": "C002",
        "name": "이*현",
        "credit_score": 634,
        "credit_grade": "5등급",
        "annual_income": 31_000_000,
        "employment_type": "계약직",
        "employment_months": 14,
        "existing_loans": [
            {"type": "카드론", "balance": 5_000_000, "monthly_payment": 150_000},
            {"type": "캐피탈론", "balance": 8_000_000, "monthly_payment": 220_000},
        ],
        "total_debt_ratio": 42.3,
        "dsr": 38.7,
        "overdue_history": True,
        "evaluated_at": "2026-06-01",
    },
}

# ─────────────────────────────────────────────
# 상담 이력 데이터
# ─────────────────────────────────────────────
_COUNSELING_HISTORY = [
    {
        "history_id": "CNS001",
        "customer_id": "C001",
        "counseling_date": "2026-05-15",
        "channel": "모바일앱",
        "topic": "신용대출 한도 문의",
        "summary": "직장인 신용대출 최대 한도 및 금리 문의. 급여이체 우대금리 0.3% 안내. 현재 신용점수 782점으로 우량 등급 안내.",
        "result": "상담 완료 (미신청)",
        "counselor": "AI상담봇",
    },
    {
        "history_id": "CNS002",
        "customer_id": "C001",
        "counseling_date": "2026-05-22",
        "channel": "콜센터",
        "topic": "전세자금대출 자격 확인",
        "summary": "버팀목 전세자금대출 자격 문의. 무주택 세대주 확인. 소득 기준 5천만원 이하 확인. 수도권 1.2억 한도 안내.",
        "result": "대출 신청 예정",
        "counselor": "박○○ 상담사",
    },
    {
        "history_id": "CNS003",
        "customer_id": "C002",
        "counseling_date": "2026-06-01",
        "channel": "지점방문",
        "topic": "고금리 대환 대출 상담",
        "summary": "캐피탈 고금리(18.9%) 대출 대환 목적 사잇돌2 대출 상담. 신용점수 634점 확인. DSR 38.7% 확인. 대환 목적 0.5% 우대금리 안내.",
        "result": "신청 진행 중",
        "counselor": "김○○ 대리",
    },
]

# ─────────────────────────────────────────────
# 영업점 정보
# ─────────────────────────────────────────────
_BRANCHES = [
    {
        "branch_id": "BR001",
        "name": "강남역 지점",
        "address": "서울 강남구 강남대로 396",
        "phone": "02-1234-5001",
        "business_hours": "평일 09:00~16:00",
        "services": ["여신상담", "대출심사", "PB서비스"],
        "parking": True,
    },
    {
        "branch_id": "BR002",
        "name": "종로 지점",
        "address": "서울 종로구 종로 33",
        "phone": "02-1234-5002",
        "business_hours": "평일 09:00~16:00",
        "services": ["여신상담", "대출심사"],
        "parking": False,
    },
    {
        "branch_id": "BR003",
        "name": "부산 서면 지점",
        "address": "부산 부산진구 서면로 68",
        "phone": "051-1234-5003",
        "business_hours": "평일 09:00~16:00",
        "services": ["여신상담", "대출심사"],
        "parking": True,
    },
]


# ════════════════════════════════════════════
# API 엔드포인트
# ════════════════════════════════════════════

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "mock-api", "version": "0.2.0"}


# ── 상품 ────────────────────────────────────

@app.get("/products")
def get_products(product_type: str | None = Query(default=None)):
    """
    대출 상품 목록 조회.
    product_type 없으면 전체 반환.
    """
    products = _PRODUCTS if not product_type else [
        p for p in _PRODUCTS if p["product_type"] == product_type
    ]
    return {
        "products": products,
        "total": len(products),
        "product_types": list({p["product_type"] for p in _PRODUCTS}),
    }


@app.get("/products/{product_id}")
def get_product_detail(product_id: str):
    """특정 상품 상세 정보 조회."""
    product = next((p for p in _PRODUCTS if p["product_id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail=f"상품을 찾을 수 없습니다: {product_id}")
    rate = _RATES.get(product_id, {})
    return {"product": product, "rate_info": rate}


# ── 금리 ────────────────────────────────────

@app.get("/rates")
def get_rates(product_id: str | None = Query(default=None)):
    """
    금리 정보 조회.
    product_id 없으면 전체 반환.
    """
    if product_id:
        rate = _RATES.get(product_id)
        if not rate:
            return {"product_id": product_id, "error": "해당 상품의 금리 정보가 없습니다"}
        return rate
    return {
        "rates": list(_RATES.values()),
        "total": len(_RATES),
        "base_rate_standard": "2026년 6월 기준",
    }


@app.get("/rates/simulation")
def simulate_repayment(
    principal: int = Query(default=30_000_000, description="대출 원금 (원). 기본값 3천만원"),
    annual_rate: float = Query(default=5.0, description="연 금리 (%). 기본값 5.0"),
    term_months: int = Query(default=36, description="대출 기간 (개월). 기본값 36개월"),
    method: str = Query(default="원리금균등", description="상환 방식"),
    grace_months: int = Query(default=0, description="거치 기간 (개월). 이자만 납부 후 균등분할 전환"),
):
    """
    월 상환금 시뮬레이션.
    원리금균등상환 / 만기일시상환 / 거치식균등분할 지원.
    """
    monthly_rate = annual_rate / 100 / 12

    if method == "만기일시상환":
        monthly_interest = int(principal * monthly_rate)
        total_interest = monthly_interest * term_months
        return {
            "principal": principal,
            "annual_rate": annual_rate,
            "term_months": term_months,
            "method": method,
            "monthly_interest": monthly_interest,
            "monthly_principal": 0,
            "monthly_payment": monthly_interest,
            "total_payment": principal + total_interest,
            "total_interest": total_interest,
            "example": f"{principal:,}원을 연 {annual_rate}%로 {term_months}개월 만기일시상환 시 월 이자 {monthly_interest:,}원",
        }

    # ── 거치식 원금균등상환 ─────────────────────────────────────────
    if method == "거치식원금균등" and grace_months > 0 and grace_months < term_months:
        repay_months = term_months - grace_months
        monthly_principal = principal // repay_months
        grace_monthly = int(principal * monthly_rate)
        grace_total = grace_monthly * grace_months
        first_repay = monthly_principal + int(principal * monthly_rate)
        last_repay  = monthly_principal + int(monthly_principal * monthly_rate)
        repay_interest = sum(
            int((principal - monthly_principal * i) * monthly_rate)
            for i in range(repay_months)
        )
        total_interest = grace_total + repay_interest
        return {
            "principal": principal,
            "annual_rate": annual_rate,
            "term_months": term_months,
            "method": "거치식원금균등상환",
            "grace_months": grace_months,
            "grace_monthly_interest": grace_monthly,
            "repay_months": repay_months,
            "monthly_principal": monthly_principal,
            "first_repay_payment": first_repay,
            "last_repay_payment": last_repay,
            "total_payment": principal + total_interest,
            "total_interest": total_interest,
            "example": (
                f"{principal:,}원 / 연 {annual_rate}% / {term_months}개월 "
                f"(거치 {grace_months}개월 이자 {grace_monthly:,}원, "
                f"원금균등 {repay_months}개월: 첫달 {first_repay:,}원 → 마지막달 {last_repay:,}원)"
            ),
        }

    # ── 거치식 원리금균등분할 ────────────────────────────────────────
    if grace_months > 0 and grace_months < term_months:
        repay_months = term_months - grace_months
        grace_monthly = int(principal * monthly_rate)
        grace_total = grace_monthly * grace_months
        if monthly_rate == 0:
            repay_monthly = principal // repay_months
        else:
            factor = (1 + monthly_rate) ** repay_months
            repay_monthly = int(principal * monthly_rate * factor / (factor - 1))
        repay_total = repay_monthly * repay_months
        total_interest = grace_total + (repay_total - principal)
        return {
            "principal": principal,
            "annual_rate": annual_rate,
            "term_months": term_months,
            "method": "거치식원리금균등상환",
            "grace_months": grace_months,
            "grace_monthly_interest": grace_monthly,
            "repay_months": repay_months,
            "repay_monthly_payment": repay_monthly,
            "total_payment": principal + total_interest,
            "total_interest": total_interest,
            "example": (
                f"{principal:,}원 / 연 {annual_rate}% / {term_months}개월 "
                f"(거치 {grace_months}개월 이자 {grace_monthly:,}원, "
                f"이후 {repay_months}개월 월 {repay_monthly:,}원)"
            ),
        }

    # ── 원금균등상환 ──────────────────────────────────────────────
    if method == "원금균등":
        monthly_principal = principal // term_months
        first_payment = monthly_principal + int(principal * monthly_rate)
        last_payment  = monthly_principal + int(monthly_principal * monthly_rate)
        total_interest = sum(
            int((principal - monthly_principal * i) * monthly_rate)
            for i in range(term_months)
        )
        return {
            "principal": principal,
            "annual_rate": annual_rate,
            "term_months": term_months,
            "method": "원금균등상환",
            "monthly_principal": monthly_principal,
            "first_payment": first_payment,
            "last_payment": last_payment,
            "total_payment": principal + total_interest,
            "total_interest": total_interest,
            "example": (
                f"{principal:,}원 / 연 {annual_rate}% / {term_months}개월 원금균등상환 "
                f"첫달 {first_payment:,}원 → 마지막달 {last_payment:,}원"
            ),
        }

    # ── 원리금균등상환 (기본) ─────────────────────────────────────
    # 공식: M = P × r(1+r)^n / ((1+r)^n - 1)
    if monthly_rate == 0:
        monthly_payment = principal // term_months
    else:
        factor = (1 + monthly_rate) ** term_months
        monthly_payment = int(principal * monthly_rate * factor / (factor - 1))

    total_payment = monthly_payment * term_months
    total_interest = total_payment - principal

    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "term_months": term_months,
        "method": "원리금균등상환",
        "monthly_payment": monthly_payment,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "example": f"{principal:,}원을 연 {annual_rate}%로 {term_months}개월 대출 시 월 {monthly_payment:,}원 상환",
    }


# ── 신용등급별 개인화 금리 ─────────────────────

# 신용등급 → 레이블 매핑
_GRADE_LABEL = {
    1: "최우량", 2: "우량", 3: "양호",
    4: "보통", 5: "보통", 6: "보통",
    7: "주의", 8: "주의",
    9: "위험", 10: "위험",
}

# 상품별·등급별 금리표 (min_rate, max_rate)
# grade 1~3: 우량 / 4~6: 일반 / 7~8: 주의 / 9~10: 위험
# 중금리 사잇돌2 대출은 4~8등급만 해당 (0.0은 해당 없음)
_PERSONALIZED_RATES: dict[str, list[tuple[float, float]]] = {
    "직장인 신용대출": [
        (3.0, 3.8), (3.5, 4.5), (4.0, 5.2),
        (5.0, 6.5), (6.0, 8.0), (7.5, 9.5),
        (9.0, 12.0), (11.0, 14.0),
        (13.0, 17.0), (16.0, 20.0),
    ],
    "프리랜서·자영업자 신용대출": [
        (4.0, 5.0), (4.5, 6.0), (5.5, 7.0),
        (6.5, 8.5), (8.0, 10.5), (9.5, 12.5),
        (11.5, 15.0), (14.0, 18.0),
        (17.0, 20.0), (19.0, 20.0),
    ],
    "중금리 사잇돌2 대출": [
        (0.0, 0.0), (0.0, 0.0), (0.0, 0.0),
        (6.5, 9.0), (8.5, 11.5), (10.0, 13.5),
        (12.0, 15.5), (14.5, 17.5),
        (0.0, 0.0), (0.0, 0.0),
    ],
    "주택담보대출": [
        (2.8, 3.4), (3.0, 3.7), (3.2, 4.0),
        (3.5, 4.5), (4.0, 5.2), (4.8, 6.2),
        (5.8, 7.5), (7.0, 9.0),
        (8.5, 11.0), (10.0, 13.0),
    ],
}


@app.get("/rates/personalized")
def get_personalized_rates(
    credit_grade: int = Query(default=5, ge=1, le=10, description="신용등급 1(최우량)~10(위험). 기본값 5"),
):
    """
    신용등급별 맞춤 금리 조회.
    credit_grade 1~10 중 하나를 입력하면 각 대출 상품별 적용 가능한 금리 범위를 반환한다.
    min_rate=max_rate=0.0 이면 해당 등급에서 이용 불가한 상품.
    """
    grade_label = _GRADE_LABEL.get(credit_grade, "보통")
    rates = []
    for product_name, grade_rates in _PERSONALIZED_RATES.items():
        min_r, max_r = grade_rates[credit_grade - 1]
        if min_r == 0.0 and max_r == 0.0:
            continue  # 해당 등급에서 이용 불가한 상품 제외
        rates.append({
            "product_name": product_name,
            "min_rate": min_r,
            "max_rate": max_r,
        })

    return {
        "credit_grade": credit_grade,
        "grade_label": grade_label,
        "rates": rates,
        "note": f"신용등급 {credit_grade}등급({grade_label}) 기준 적용 금리이며, 우대금리 조건에 따라 추가 인하 가능합니다.",
    }


# ── 정책/약관 ────────────────────────────────

@app.get("/policies")
def get_policies(policy_type: str | None = Query(default=None)):
    """
    정책/약관 조회.
    policy_type 없으면 전체 반환.
    """
    policies = _POLICIES if not policy_type else [
        p for p in _POLICIES if p["policy_type"] == policy_type
    ]
    return {
        "policies": policies,
        "total": len(policies),
        "policy_types": list({p["policy_type"] for p in _POLICIES}),
    }


# ── 서류 ────────────────────────────────────

@app.get("/documents/search")
def search_documents(
    keyword: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    """
    필요서류 검색.
    keyword / product_id / category 필터 조합 가능.
    """
    docs = _DOCUMENTS
    if keyword:
        keyword_lower = keyword.lower()
        docs = [d for d in docs if keyword_lower in d["name"].lower() or keyword_lower in d["description"].lower()]
    if product_id:
        docs = [d for d in docs if product_id in d["applicable_products"] or "ALL" in d["applicable_products"]]
    if category:
        docs = [d for d in docs if d["category"] == category]

    return {
        "documents": docs,
        "total": len(docs),
        "categories": list({d["category"] for d in _DOCUMENTS}),
    }


# ── 고객 신용 ────────────────────────────────

@app.get("/customers/credit")
def get_customer_credit(customer_id: str = Query(..., description="고객 ID")):
    """
    고객 신용 정보 조회 (Mock).
    실제 환경에서는 KCB/NICE 연동 또는 내부 신용평가 시스템 호출.
    """
    customer = _MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        # Mock 고객이 없으면 기본 데이터 반환
        return {
            "customer_id": customer_id,
            "credit_score": 720,
            "credit_grade": "3등급",
            "annual_income": 40_000_000,
            "employment_type": "정규직",
            "employment_months": 24,
            "existing_loans": [],
            "total_debt_ratio": 0,
            "dsr": 0,
            "overdue_history": False,
            "evaluated_at": "2026-06-01",
            "note": "Mock 기본 데이터",
        }
    return customer


# ── 신청 자격 ────────────────────────────────

@app.get("/applications/eligibility")
def check_eligibility(
    product_id: str = Query(default="P001", description="신청 상품 ID. 기본값 P001(직장인 신용대출)"),
    annual_income: int = Query(default=40_000_000, description="연 소득 (원). 기본값 4천만원"),
    credit_score: int = Query(default=700, description="신용점수. 기본값 700점"),
    employment_months: int = Query(default=12, description="현 직장 근무 기간 (개월). 기본값 12개월"),
    existing_monthly_payment: int = Query(default=0, description="기존 대출 월 상환액 (원)"),
    loan_amount: int = Query(default=30_000_000, description="희망 대출금액 (원). 기본값 3천만원"),
    loan_term_months: int = Query(default=36, description="희망 대출기간 (개월). 기본값 36개월"),
):
    """
    대출 신청 자격 사전 검토 (Mock).
    실제 심사와 다를 수 있으며, 최종 결과는 정식 심사에서 결정됩니다.
    """
    product = next((p for p in _PRODUCTS if p["product_id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail=f"상품을 찾을 수 없습니다: {product_id}")

    rate_info = _RATES.get(product_id, {})
    estimated_rate = rate_info.get("min_final_rate", product["min_rate"])

    # DSR 계산: (기존 월 상환액 + 신규 월 상환액) / 월 소득
    monthly_income = annual_income / 12
    monthly_rate = estimated_rate / 100 / 12
    if monthly_rate > 0 and loan_amount > 0:
        factor = (1 + monthly_rate) ** loan_term_months
        new_monthly_payment = int(loan_amount * monthly_rate * factor / (factor - 1))
    else:
        new_monthly_payment = 0
    total_monthly_payment = existing_monthly_payment + new_monthly_payment
    dsr = (total_monthly_payment / monthly_income * 100) if monthly_income > 0 else 0

    issues = []
    warnings = []

    # 신용점수 체크
    min_score = 650 if product_id in ["P001", "P007"] else 600 if product_id == "P003" else 0
    if credit_score < min_score:
        issues.append(f"신용점수 {credit_score}점 — 최소 {min_score}점 이상 필요")

    # 소득 체크
    min_income = 30_000_000 if product_id in ["P001", "P002"] else 0
    if annual_income < min_income:
        issues.append(f"연소득 {annual_income:,}원 — 최소 {min_income:,}원 이상 필요")

    # 근무기간 체크
    min_months = 3 if product_id == "P001" else 12 if product_id == "P002" else 0
    if employment_months < min_months:
        issues.append(f"근무기간 {employment_months}개월 — 최소 {min_months}개월 이상 필요")

    # DSR 체크
    if dsr > 40:
        issues.append(f"DSR {dsr:.1f}% — 40% 초과로 대출 한도 축소 또는 거절 가능")
    elif dsr > 30:
        warnings.append(f"DSR {dsr:.1f}% — 30% 초과, 한도 축소 가능성 있음")

    # 희망 금액 한도 체크
    if loan_amount > product["max_amount"]:
        issues.append(f"희망 금액 {loan_amount:,}원 — 상품 최대 한도 {product['max_amount']:,}원 초과")

    eligible = len(issues) == 0

    return {
        "product_id": product_id,
        "product_name": product["name"],
        "eligible": eligible,
        "estimated_rate": estimated_rate,
        "new_monthly_payment": new_monthly_payment,
        "estimated_dsr": round(dsr, 1),
        "issues": issues,
        "warnings": warnings,
        "recommendation": (
            "신청 가능합니다. 정식 심사 후 최종 한도와 금리가 결정됩니다."
            if eligible else
            "현재 조건으로는 신청이 어렵습니다. 아래 이슈 사항을 확인하세요."
        ),
    }


# ── 상담 이력 ────────────────────────────────

@app.get("/counseling/history")
def get_counseling_history(customer_id: str | None = Query(default=None, description="고객 ID. 미입력 시 전체 이력 반환")):
    """고객 상담 이력 조회. customer_id 없으면 전체 반환."""
    histories = (
        [h for h in _COUNSELING_HISTORY if h["customer_id"] == customer_id]
        if customer_id
        else _COUNSELING_HISTORY
    )
    return {
        "customer_id": customer_id or "ALL",
        "histories": histories,
        "total": len(histories),
    }


# ── 영업점 ────────────────────────────────

@app.get("/branches")
def get_branches(region: str | None = Query(default=None)):
    """영업점 정보 조회."""
    branches = _BRANCHES if not region else [
        b for b in _BRANCHES if region in b["address"]
    ]
    return {"branches": branches, "total": len(branches)}


# ════════════════════════════════════════════
# 외화 거래 (Forex) 엔드포인트
# ════════════════════════════════════════════

# ─────────────────────────────────────────────
# 환율 데이터 (2026-06-15 기준 모의 데이터)
# ─────────────────────────────────────────────
_EXCHANGE_RATES = [
    {"currency": "USD", "name": "미국 달러",       "buy": 1_328.50, "sell": 1_355.50, "standard": 1_342.00, "change": +2.50,  "change_pct": +0.19},
    {"currency": "JPY", "name": "일본 엔 (100엔)", "buy":   883.20, "sell":   900.80, "standard":   892.00, "change": -1.20,  "change_pct": -0.13},
    {"currency": "EUR", "name": "유럽 유로",        "buy": 1_435.60, "sell": 1_464.40, "standard": 1_450.00, "change": +5.00,  "change_pct": +0.35},
    {"currency": "CNY", "name": "중국 위안",        "buy":   181.40, "sell":   185.60, "standard":   183.50, "change": +0.30,  "change_pct": +0.16},
    {"currency": "GBP", "name": "영국 파운드",      "buy": 1_686.20, "sell": 1_720.80, "standard": 1_703.50, "change": +8.50,  "change_pct": +0.50},
    {"currency": "AUD", "name": "호주 달러",        "buy":   855.70, "sell":   873.30, "standard":   864.50, "change": -0.50,  "change_pct": -0.06},
    {"currency": "HKD", "name": "홍콩 달러",        "buy":   168.20, "sell":   171.80, "standard":   170.00, "change": +0.10,  "change_pct": +0.06},
]

# 외화예금 금리 (연이율, %)
_FOREIGN_DEPOSIT_RATES = [
    {"currency": "USD", "name": "미국 달러", "demand_rate": 0.10, "time_deposit_6m": 3.80, "time_deposit_12m": 4.10, "min_amount_usd": 100},
    {"currency": "JPY", "name": "일본 엔",   "demand_rate": 0.01, "time_deposit_6m": 0.10, "time_deposit_12m": 0.15, "min_amount_usd": 100},
    {"currency": "EUR", "name": "유럽 유로", "demand_rate": 0.05, "time_deposit_6m": 2.50, "time_deposit_12m": 2.80, "min_amount_usd": 100},
    {"currency": "CNY", "name": "중국 위안", "demand_rate": 0.10, "time_deposit_6m": 1.80, "time_deposit_12m": 2.20, "min_amount_usd": 100},
]

# 해외송금 수수료 테이블 (USD 기준)
_REMITTANCE_FEE_TABLE = [
    {"range": "500달러 이하",          "fee_krw": 5_000,  "fee_usd": None},
    {"range": "500달러 초과 ~ 5,000달러", "fee_krw": 10_000, "fee_usd": None},
    {"range": "5,000달러 초과",         "fee_krw": 20_000, "fee_usd": None},
]


@app.get("/forex/rates")
def get_forex_rates(
    currency: str | None = Query(default=None, description="통화 코드 (USD, JPY, EUR, CNY 등). 미입력 시 전체 조회"),
):
    """주요 통화 환율 조회 (매매기준율/현찰 살 때/팔 때)."""
    if currency:
        rate = next((r for r in _EXCHANGE_RATES if r["currency"].upper() == currency.upper()), None)
        if not rate:
            raise HTTPException(status_code=404, detail=f"지원하지 않는 통화: {currency}")
        return {"rates": [rate], "base_currency": "KRW", "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+09:00")}
    return {
        "rates": _EXCHANGE_RATES,
        "base_currency": "KRW",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "note": "현찰 기준 환율이며 Mock 고정 데이터입니다. 우대 환율은 채널에 따라 달라집니다.",
    }


@app.get("/forex/exchange-calc")
def calc_currency_exchange(
    from_currency: str          = Query(default="KRW",      description="출발 통화 코드 (예: KRW, USD)"),
    to_currency:   str          = Query(default="USD",      description="도착 통화 코드 (예: USD, JPY)"),
    amount:        float        = Query(default=1_000_000,  description="환전 금액 (출발 통화 기준). target_amount 지정 시 무시"),
    target_amount: float | None = Query(default=None,       description="수취 희망 금액 (도착 통화 기준). KRW→외화 역산 계산 시 사용"),
    channel:       str          = Query(default="BRANCH",   description="채널 (INTERNET | MOBILE | BRANCH). 기본값 BRANCH"),
    customer_id:   str | None   = Query(default=None,       description="고객 ID. 인터넷·모바일 등록 고객 여부 확인에 사용"),
):
    """원화 ↔ 외화 환전 계산.

    우대율 기준:
    - INTERNET / MOBILE 채널 또는 customer_id 제공 시: 스프레드 50% 우대
    - BRANCH 채널이며 customer_id 없음: 우대 없이 기준 스프레드 전액 적용

    역산(target_amount):
    - KRW→외화 방향에서 target_amount 지정 시 "N USD를 받으려면 원화 얼마?"를 계산
    """
    from_c = from_currency.upper()
    to_c   = to_currency.upper()
    ch     = channel.upper()

    # 우대율: 인터넷·모바일 채널이거나 고객 ID가 확인된 경우에만 50% 적용
    is_preferential = ch in ("INTERNET", "MOBILE") or customer_id is not None
    discount_rate   = 50 if is_preferential else 0
    is_reverse_calc = False

    def _get_rate(code: str) -> dict | None:
        return next((x for x in _EXCHANGE_RATES if x["currency"] == code), None)

    if from_c == "KRW" and to_c != "KRW":
        # KRW → 외화: 고객이 외화를 '사는' 것 → 은행 현찰 팔 때(sell) 요율 기준
        row = _get_rate(to_c)
        if not row:
            raise HTTPException(status_code=404, detail=f"지원하지 않는 통화: {to_c}")
        std          = row["standard"]
        spread       = row["sell"] - std          # 양수: 고객 불리 방향
        rate_applied = std + spread * (1 - discount_rate / 100)
        if target_amount is not None:
            # 역산: 목표 수취 외화 → 필요 원화 계산
            is_reverse_calc = True
            fee    = 3_000 if target_amount < 1_000 else 5_000
            amount = round(target_amount * rate_applied + fee, 0)  # 필요 원화
            to_amount = target_amount
        else:
            fee       = 3_000 if amount < 1_000_000 else 5_000
            to_amount = round((amount - fee) / rate_applied, 2) if rate_applied > 0 else 0

    elif from_c != "KRW" and to_c == "KRW":
        # 외화 → KRW: 고객이 외화를 '파는' 것 → 은행 현찰 살 때(buy) 요율 기준
        row = _get_rate(from_c)
        if not row:
            raise HTTPException(status_code=404, detail=f"지원하지 않는 통화: {from_c}")
        std          = row["standard"]
        spread       = std - row["buy"]           # 양수: 고객 불리 방향
        rate_applied = std - spread * (1 - discount_rate / 100)
        fee          = 3_000 if amount < 1_000 else 5_000
        to_amount    = round(amount * rate_applied - fee, 0)

    else:
        raise HTTPException(status_code=400, detail="KRW ↔ 외화 변환만 지원합니다. (예: KRW→USD 또는 USD→KRW)")

    note_parts = []
    if is_preferential:
        note_parts.append(f"인터넷·모바일 환전 우대율 {discount_rate}% 적용")
    else:
        note_parts.append("우대율 미적용 (영업점 기준 환율). 인터넷·모바일 채널 이용 시 최대 50% 우대 가능")
    note_parts.append("본 안내는 참고 목적이며, 실제 적용 환율은 거래 시점에 확정됩니다.")

    return {
        "from_currency":  from_c,
        "to_currency":    to_c,
        "from_amount":    amount,
        "to_amount":      to_amount,
        "rate_applied":   round(rate_applied, 2),
        "standard_rate":  row["standard"],
        "buy_rate":       row["buy"],    # 은행 살때 (고객이 외화 팔 때)
        "sell_rate":      row["sell"],   # 은행 팔때 (고객이 외화 살 때)
        "fee_krw":        fee,
        "channel":        ch,
        "customer_id":    customer_id,
        "discount_rate":  discount_rate,
        "is_reverse_calc": is_reverse_calc,   # True: 목표 금액 역산 (원→달러 N달러 수취)
        "note":           " ".join(note_parts),
        "timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+09:00"),
    }


@app.get("/forex/remittance")
def get_remittance_info(
    destination_country: str | None = Query(default=None, description="수취국 코드 (예: US, JP). 미입력 시 공통 안내"),
    amount: float | None = Query(default=None, description="송금 금액 (USD 기준)"),
):
    """해외송금 한도, 수수료, 소요 시간, 방법 안내."""
    methods = [
        {
            "method": "인터넷·모바일 송금",
            "fee":    _REMITTANCE_FEE_TABLE,
            "processing_time": "당일~익영업일 (수취국 영업일 기준)",
            "daily_limit_usd": 50_000,
            "annual_limit_usd": 500_000,
            "required_docs": ["신분증", "외국환거래 신청서 (앱 내 작성)"],
        },
        {
            "method": "영업점 창구 송금",
            "fee":    _REMITTANCE_FEE_TABLE,
            "processing_time": "당일~3영업일",
            "daily_limit_usd": 100_000,
            "annual_limit_usd": None,
            "required_docs": ["신분증", "외국환거래 신청서", "5만 달러 초과 시 증빙서류"],
        },
    ]

    country_info = None
    if destination_country:
        country_map = {
            "US": {"name": "미국", "swift_available": True, "notes": "FED Wire / SWIFT 모두 지원. 평균 1영업일 소요."},
            "JP": {"name": "일본", "swift_available": True, "notes": "SWIFT 지원. 일본 은행 계좌번호 필요."},
            "CN": {"name": "중국", "swift_available": True, "notes": "위안화 수취 가능. CNAPS 코드 필요."},
            "VN": {"name": "베트남", "swift_available": True, "notes": "영업일 기준 2~3일 소요."},
        }
        country_info = country_map.get(destination_country.upper(), {
            "name": destination_country,
            "swift_available": True,
            "notes": "SWIFT 네트워크 통해 송금. 수취은행 SWIFT 코드 필요.",
        })

    fee_estimate = None
    if amount is not None:
        if amount <= 500:
            fee_estimate = 5_000
        elif amount <= 5_000:
            fee_estimate = 10_000
        else:
            fee_estimate = 20_000

    return {
        "methods":              methods,
        "destination_country":  country_info,
        "fee_estimate_krw":     fee_estimate,
        "daily_limit_usd":      50_000,
        "caution":              "해외 테러·불법 자금 방지를 위해 고액 송금 시 목적 증빙이 필요할 수 있습니다.",
    }


@app.get("/forex/deposit-rates")
def get_foreign_deposit_rates(
    currency: str | None = Query(default=None, description="통화 코드 (USD, JPY, EUR, CNY). 미입력 시 전체"),
):
    """외화예금 금리 및 가입 조건 조회."""
    rates = (
        [r for r in _FOREIGN_DEPOSIT_RATES if r["currency"].upper() == currency.upper()]
        if currency
        else _FOREIGN_DEPOSIT_RATES
    )
    if currency and not rates:
        raise HTTPException(status_code=404, detail=f"지원하지 않는 통화: {currency}")
    return {
        "deposit_rates": rates,
        "note": "금리는 세전 기준이며, 시장 상황에 따라 변경될 수 있습니다. 이자소득세(15.4%) 부과.",
        "min_deposit":   "각 통화별 최소 가입 금액 상이 (USD 기준 $100 이상)",
    }


# ════════════════════════════════════════════
# 알림 (Notification) 엔드포인트
# ════════════════════════════════════════════

# ─────────────────────────────────────────────
# Mock 알림 규칙 데이터
# ─────────────────────────────────────────────
_NOTIFICATION_RULES = [
    {
        "rule_id":          "RULE_RATE_CHANGE",
        "name":             "금리 변동 알림",
        "trigger_type":     "RATE_CHANGE",
        "channel":          "PUSH",
        "message_template": "[금리 변동 알림] {product_name}의 금리가 {old_rate}% → {new_rate}%로 변경되었습니다.",
        "threshold":        0.1,
        "is_active":        True,
        "description":      "대출 상품 금리가 0.1% 이상 변동 시 즉시 푸시 알림",
    },
    {
        "rule_id":          "RULE_MATURITY_30",
        "name":             "만기 30일 전 알림",
        "trigger_type":     "MATURITY",
        "channel":          "SMS",
        "message_template": "[만기 안내] {product_name} 대출 만기일이 30일 후({date})입니다. 연장·상환 계획을 확인하세요.",
        "threshold":        30.0,
        "is_active":        True,
        "description":      "대출 만기 30일 전 문자 발송",
    },
    {
        "rule_id":          "RULE_MATURITY_7",
        "name":             "만기 7일 전 알림",
        "trigger_type":     "MATURITY",
        "channel":          "PUSH",
        "message_template": "[긴급] {product_name} 대출 만기가 7일 후({date})입니다. 즉시 확인이 필요합니다.",
        "threshold":        7.0,
        "is_active":        True,
        "description":      "대출 만기 7일 전 푸시 알림 (긴급)",
    },
    {
        "rule_id":          "RULE_OVERDUE_1",
        "name":             "연체 1일 경보",
        "trigger_type":     "OVERDUE",
        "channel":          "PUSH",
        "message_template": "[연체 알림] {product_name} 납입일이 경과했습니다. 연체이자 발생을 방지하기 위해 즉시 납부하세요.",
        "threshold":        1.0,
        "is_active":        True,
        "description":      "납입 기일 다음날 즉시 연체 경보",
    },
    {
        "rule_id":          "RULE_LIMIT_USAGE_90",
        "name":             "한도 90% 소진 알림",
        "trigger_type":     "LIMIT_USAGE",
        "channel":          "IN_APP",
        "message_template": "[한도 경고] 마이너스통장 한도의 90% 이상({usage_rate}%)을 사용 중입니다. 잔여 한도를 확인하세요.",
        "threshold":        90.0,
        "is_active":        True,
        "description":      "한도대출 사용률 90% 초과 시 인앱 알림",
    },
    {
        "rule_id":          "RULE_GRADE_UP",
        "name":             "신용등급 상승 알림",
        "trigger_type":     "GRADE_UP",
        "channel":          "PUSH",
        "message_template": "[신용등급 상승] 신용등급이 {old_grade}등급에서 {new_grade}등급으로 개선되었습니다! 금리 인하 신청이 가능합니다.",
        "threshold":        None,
        "is_active":        True,
        "description":      "신용등급 향상 시 금리 인하 기회 안내 푸시",
    },
]

_notification_log_counter = {"count": 0}


class NotificationSendRequest(BaseModel):
    rule_id: str
    customer_id: str
    trigger_data: dict | None = None


@app.get("/notifications/rules")
def get_notification_rules(
    trigger_type: str | None = Query(default=None, description="RATE_CHANGE / MATURITY / OVERDUE / LIMIT_USAGE / GRADE_UP"),
    is_active:    bool | None = Query(default=None, description="활성 여부 필터"),
):
    """등록된 알림 규칙 목록 조회."""
    rules = _NOTIFICATION_RULES
    if trigger_type:
        rules = [r for r in rules if r["trigger_type"] == trigger_type.upper()]
    if is_active is not None:
        rules = [r for r in rules if r["is_active"] == is_active]
    return {"rules": rules, "total": len(rules)}


@app.post("/notifications/send")
def send_notification(req: NotificationSendRequest):
    """알림 발송 (Mock). 실제 발송 없이 성공 응답만 반환."""
    rule = next((r for r in _NOTIFICATION_RULES if r["rule_id"] == req.rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail=f"알림 규칙을 찾을 수 없습니다: {req.rule_id}")

    _notification_log_counter["count"] += 1
    log_id = _notification_log_counter["count"]

    template = rule["message_template"]
    trigger = req.trigger_data or {}
    try:
        message = template.format(**trigger)
    except KeyError:
        message = template  # 템플릿 변수 없으면 원문 사용

    return {
        "status":      "SENT",
        "log_id":      log_id,
        "rule_id":     req.rule_id,
        "customer_id": req.customer_id,
        "channel":     rule["channel"],
        "message":     message,
        "note":        "Mock 발송 — 실제 채널로 전송되지 않습니다.",
    }
