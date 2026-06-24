from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge_model import ApiCatalog

TOOLS = [
    # ── 기존 4개 ──────────────────────────────────────────────────
    {
        "api_id": "MOCK_PRODUCT_LOOKUP",
        "name": "대출 상품 목록 조회",
        "endpoint_path": "/products",
        "method": "GET",
        "description": "전체 대출 상품 목록 및 조건 조회 (신용대출/전세/담보/한도 등)",
        "request_schema": {"type": "object", "properties": {"product_type": {"type": "string"}}},
        "response_schema": {"type": "object", "properties": {"products": {"type": "array"}, "total": {"type": "integer"}}},
    },
    {
        "api_id": "MOCK_RATE_LOOKUP",
        "name": "금리 및 우대금리 조회",
        "endpoint_path": "/rates",
        "method": "GET",
        "description": "상품별 기준금리, 우대금리 조건, 최종금리 범위 조회",
        "request_schema": {"type": "object", "properties": {"product_id": {"type": "string"}}},
        "response_schema": {"type": "object", "properties": {"rates": {"type": "array"}}},
    },
    {
        "api_id": "MOCK_POLICY_LOOKUP",
        "name": "여신 정책/약관 조회",
        "endpoint_path": "/policies",
        "method": "GET",
        "description": "신용심사 기준, LTV/DSR 한도, 우대금리 조건, 중도상환수수료, 연체정책 조회",
        "request_schema": {"type": "object", "properties": {"policy_type": {"type": "string"}}},
        "response_schema": {"type": "object", "properties": {"policies": {"type": "array"}}},
    },
    {
        "api_id": "MOCK_DOCUMENT_SEARCH",
        "name": "필요서류 검색",
        "endpoint_path": "/documents/search",
        "method": "GET",
        "description": "대출 종류·고객 유형별 제출 서류 목록 조회 (소득증빙/담보/우대자격 등)",
        "request_schema": {"type": "object", "properties": {"keyword": {"type": "string"}, "product_id": {"type": "string"}, "category": {"type": "string"}}},
        "response_schema": {"type": "object", "properties": {"documents": {"type": "array"}, "total": {"type": "integer"}}},
    },
    # ── 신규 4개 ──────────────────────────────────────────────────
    {
        "api_id": "MOCK_RATE_SIMULATION",
        "name": "월 상환금 시뮬레이션",
        "endpoint_path": "/rates/simulation",
        "method": "GET",
        "description": "대출 원금·금리·기간으로 월 납입금, 총 이자 계산",
        "request_schema": {
            "type": "object",
            "properties": {
                "principal": {"type": "integer", "description": "대출 원금(원)"},
                "annual_rate": {"type": "number", "description": "연 금리(%)"},
                "term_months": {"type": "integer", "description": "대출 기간(개월)"},
                "method": {"type": "string", "description": "상환방식"},
            },
        },
        "response_schema": {"type": "object", "properties": {"monthly_payment": {"type": "integer"}, "total_interest": {"type": "integer"}}},
    },
    {
        "api_id": "MOCK_ELIGIBILITY_CHECK",
        "name": "대출 신청 자격 사전 확인",
        "endpoint_path": "/applications/eligibility",
        "method": "GET",
        "description": "소득·신용점수·DSR 기준으로 신청 가능 여부 및 예상 금리 사전 검토",
        "request_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "annual_income": {"type": "integer"},
                "credit_score": {"type": "integer"},
                "employment_months": {"type": "integer"},
            },
        },
        "response_schema": {"type": "object", "properties": {"eligible": {"type": "boolean"}, "issues": {"type": "array"}}},
    },
    {
        "api_id": "MOCK_COUNSELING_HISTORY",
        "name": "고객 상담 이력 조회",
        "endpoint_path": "/counseling/history",
        "method": "GET",
        "description": "고객별 과거 상담 채널·주제·결과 이력 조회",
        "request_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}},
        "response_schema": {"type": "object", "properties": {"histories": {"type": "array"}, "total": {"type": "integer"}}},
    },
    {
        "api_id": "MOCK_BRANCH_LOOKUP",
        "name": "영업점 정보 조회",
        "endpoint_path": "/branches",
        "method": "GET",
        "description": "지역별 영업점 위치, 전화번호, 운영시간, 제공 서비스 조회",
        "request_schema": {"type": "object", "properties": {"region": {"type": "string"}}},
        "response_schema": {"type": "object", "properties": {"branches": {"type": "array"}}},
    },
    {
        "api_id": "MOCK_PERSONALIZED_RATE_LOOKUP",
        "name": "신용등급별 개인화 금리 조회",
        "endpoint_path": "/rates/personalized",
        "method": "GET",
        "description": "고객 신용등급(1~10)을 기반으로 상품별 적용 가능한 금리 범위 조회",
        "request_schema": {
            "type": "object",
            "properties": {
                "credit_grade": {"type": "integer", "minimum": 1, "maximum": 10, "description": "신용등급 1(최우량)~10(위험)"},
            },
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "credit_grade": {"type": "integer"},
                "grade_label": {"type": "string"},
                "rates": {"type": "array"},
                "note": {"type": "string"},
            },
        },
    },
    # ── 외화 거래 4개 ──────────────────────────────────────────────
    {
        "api_id": "MOCK_EXCHANGE_RATE_LOOKUP",
        "name": "실시간 환율 조회",
        "endpoint_path": "/forex/rates",
        "method": "GET",
        "description": "주요 통화(USD, JPY, EUR, CNY 등)의 현재 환율, 전일 대비 변동폭 조회",
        "request_schema": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "통화 코드 (예: USD, JPY). 미입력 시 전체 조회"},
            },
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "rates": {"type": "array"},
                "base_currency": {"type": "string"},
                "timestamp": {"type": "string"},
            },
        },
    },
    {
        "api_id": "MOCK_CURRENCY_EXCHANGE_CALC",
        "name": "외화 환전 계산",
        "endpoint_path": "/forex/exchange-calc",
        "method": "GET",
        "description": "원화 → 외화 또는 외화 → 원화 환전 시 수령액, 수수료, 우대율 계산",
        "request_schema": {
            "type": "object",
            "properties": {
                "from_currency": {"type": "string", "description": "출발 통화 코드 (예: KRW)"},
                "to_currency":   {"type": "string", "description": "도착 통화 코드 (예: USD)"},
                "amount":        {"type": "number", "description": "환전 금액"},
            },
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "from_amount": {"type": "number"},
                "to_amount":   {"type": "number"},
                "rate_applied": {"type": "number"},
                "fee":          {"type": "number"},
                "discount_rate": {"type": "number"},
            },
        },
    },
    {
        "api_id": "MOCK_FOREIGN_REMITTANCE",
        "name": "해외송금 안내",
        "endpoint_path": "/forex/remittance",
        "method": "GET",
        "description": "해외송금 한도, 수수료, 소요 시간, 필요 서류, 송금 방법 안내",
        "request_schema": {
            "type": "object",
            "properties": {
                "destination_country": {"type": "string", "description": "수취국 (예: US, JP)"},
                "amount": {"type": "number", "description": "송금 금액 (USD 기준)"},
            },
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "methods": {"type": "array"},
                "daily_limit_usd": {"type": "number"},
                "fee_table": {"type": "array"},
            },
        },
    },
    {
        "api_id": "MOCK_FOREIGN_DEPOSIT_RATE",
        "name": "외화예금 금리 조회",
        "endpoint_path": "/forex/deposit-rates",
        "method": "GET",
        "description": "통화별 외화예금 금리(보통예금/정기예금) 및 가입 조건 조회",
        "request_schema": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "통화 코드 (예: USD, JPY). 미입력 시 전체"},
            },
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "deposit_rates": {"type": "array"},
            },
        },
    },
    # ── 알림 2개 ───────────────────────────────────────────────────
    {
        "api_id": "MOCK_NOTIFICATION_RULES",
        "name": "알림 규칙 조회",
        "endpoint_path": "/notifications/rules",
        "method": "GET",
        "description": "등록된 알림 규칙 목록 조회. trigger_type으로 필터링 가능",
        "request_schema": {
            "type": "object",
            "properties": {
                "trigger_type": {"type": "string", "description": "RATE_CHANGE / MATURITY / OVERDUE / LIMIT_USAGE / GRADE_UP"},
                "is_active":    {"type": "boolean"},
            },
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "rules": {"type": "array"},
                "total": {"type": "integer"},
            },
        },
    },
    {
        "api_id": "MOCK_NOTIFICATION_SEND",
        "name": "알림 발송",
        "endpoint_path": "/notifications/send",
        "method": "POST",
        "description": "지정된 규칙 ID와 고객 ID로 알림 메시지를 생성하고 발송 이력을 기록",
        "request_schema": {
            "type": "object",
            "properties": {
                "rule_id":     {"type": "string"},
                "customer_id": {"type": "string"},
                "trigger_data": {"type": "object"},
            },
            "required": ["rule_id", "customer_id"],
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "status":  {"type": "string"},
                "message": {"type": "string"},
                "log_id":  {"type": "integer"},
            },
        },
    },
]


def seed_tools(db: Session) -> None:
    base_url = settings.MOCK_API_URL.rstrip("/")
    for data in TOOLS:
        existing = db.query(ApiCatalog).filter_by(api_id=data["api_id"]).first()
        if existing is None:
            db.add(
                ApiCatalog(
                    api_id=data["api_id"],
                    name=data["name"],
                    endpoint=f"{base_url}{data['endpoint_path']}",
                    method=data["method"],
                    description=data["description"],
                    request_schema=data["request_schema"],
                    response_schema=data["response_schema"],
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
            )

    db.commit()
    print(f"[tools_seed] {len(TOOLS)} tools seeded.")
