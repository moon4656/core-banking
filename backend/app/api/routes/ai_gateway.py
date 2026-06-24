from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.leader import LeaderAgent
from app.core.database import get_db
from app.core.security import AuthContext, require_analyst_context
from app.schemas.ai_gateway import (
    ChatRequest,
    ChatResponse,
    ScenarioItem,
    ScenarioListResponse,
)
from app.trace.trace_service import Timer, count_events, count_evidence, record_event

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

# ─────────────────────────────────────────────────────────────
# 시나리오 카탈로그 — 카테고리별 사전 정의된 Chat 테스트 질문 모음
# ─────────────────────────────────────────────────────────────
_SCENARIOS: list[ScenarioItem] = [
    # ── 외화 거래 (forex) ────────────────────────────────────────
    ScenarioItem(
        id="FX-001",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="오늘 달러 환율 얼마야?",
        description="미국 달러(USD) 현재 환율 조회. MOCK_EXCHANGE_RATE_LOOKUP 호출 확인.",
        expected_concepts=["CONCEPT_EXCHANGE_RATE"],
        expected_api="MOCK_EXCHANGE_RATE_LOOKUP",
        tags=["환율", "달러", "USD"],
    ),
    ScenarioItem(
        id="FX-002",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="주요 통화 환율 다 알려줘",
        description="USD·JPY·EUR·CNY 전체 환율 조회. 다중 통화 응답 포맷 검증.",
        expected_concepts=["CONCEPT_EXCHANGE_RATE"],
        expected_api="MOCK_EXCHANGE_RATE_LOOKUP",
        tags=["환율", "전체통화", "다중결과"],
    ),
    ScenarioItem(
        id="FX-003",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="100만원 달러로 환전하면 얼마야?",
        description="KRW→USD 환전 계산. 금액 파라미터 추출 및 수수료 계산 검증.",
        expected_concepts=["CONCEPT_CURRENCY_EXCHANGE"],
        expected_api="MOCK_CURRENCY_EXCHANGE_CALC",
        tags=["환전", "달러", "금액계산"],
    ),
    ScenarioItem(
        id="FX-004",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="50만원 엔화로 환전하면 얼마나 받아?",
        description="KRW→JPY 환전 계산. 엔화 통화 파라미터 추출 검증.",
        expected_concepts=["CONCEPT_CURRENCY_EXCHANGE"],
        expected_api="MOCK_CURRENCY_EXCHANGE_CALC",
        tags=["환전", "엔화", "JPY"],
    ),
    ScenarioItem(
        id="FX-005",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="해외 송금하려면 어떻게 해?",
        description="해외송금 한도·수수료·방법 안내. MOCK_FOREIGN_REMITTANCE 호출 확인.",
        expected_concepts=["CONCEPT_FOREIGN_REMITTANCE"],
        expected_api="MOCK_FOREIGN_REMITTANCE",
        tags=["해외송금", "송금", "수수료"],
    ),
    ScenarioItem(
        id="FX-006",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="미국으로 1000달러 송금하면 수수료 얼마야?",
        description="특정 수취국(US) + 금액 파라미터 추출. 수수료 예상액 계산 검증.",
        expected_concepts=["CONCEPT_FOREIGN_REMITTANCE"],
        expected_api="MOCK_FOREIGN_REMITTANCE",
        tags=["해외송금", "미국", "수수료계산"],
    ),
    ScenarioItem(
        id="FX-007",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="달러 예금 금리 얼마야?",
        description="USD 외화예금 금리 조회. 보통예금·정기예금 구분 응답 검증.",
        expected_concepts=["CONCEPT_FOREIGN_DEPOSIT"],
        expected_api="MOCK_FOREIGN_DEPOSIT_RATE",
        tags=["외화예금", "달러", "금리"],
    ),
    ScenarioItem(
        id="FX-008",
        category="forex",
        agent="FOREX_AGENT",
        intent="INQUIRY",
        message="외화예금 금리 전체 알려줘",
        description="USD·JPY·EUR·CNY 전 통화 외화예금 금리 조회.",
        expected_concepts=["CONCEPT_FOREIGN_DEPOSIT"],
        expected_api="MOCK_FOREIGN_DEPOSIT_RATE",
        tags=["외화예금", "전체통화"],
    ),
    ScenarioItem(
        id="FX-009",
        category="forex",
        agent="FOREX_AGENT",
        intent="COMPARISON",
        message="달러 환율이랑 유로 환율 비교해줘",
        description="USD vs EUR 환율 비교 질문. COMPARISON 의도 탐지 및 다중 통화 응답 검증.",
        expected_concepts=["CONCEPT_EXCHANGE_RATE"],
        expected_api="MOCK_EXCHANGE_RATE_LOOKUP",
        tags=["환율", "비교", "달러", "유로"],
    ),
    # ── 알림 (notification) ───────────────────────────────────────
    ScenarioItem(
        id="NT-001",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="알림 규칙 전체 보여줘",
        description="등록된 전체 알림 규칙 조회. MOCK_NOTIFICATION_RULES 호출 및 6건 규칙 확인.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "규칙", "전체조회"],
    ),
    ScenarioItem(
        id="NT-002",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="금리 변동 알림 규칙 보여줘",
        description="RATE_CHANGE 트리거 알림 규칙만 필터링 조회. trigger_type 파라미터 전달 검증.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "금리변동", "RATE_CHANGE"],
    ),
    ScenarioItem(
        id="NT-003",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="만기 알림은 어떻게 설정돼 있어?",
        description="MATURITY 트리거 알림 규칙 조회. 30일/7일 전 알림 규칙 2건 확인.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "만기", "MATURITY"],
    ),
    ScenarioItem(
        id="NT-004",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="연체 알림 규칙 알려줘",
        description="OVERDUE 트리거 알림 규칙 조회. 연체 1일 경보 규칙 확인.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "연체", "OVERDUE"],
    ),
    ScenarioItem(
        id="NT-005",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="한도 소진 알림 설정 보여줘",
        description="LIMIT_USAGE 트리거 알림 규칙 조회. 90% 소진 경보 규칙 확인.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "한도소진", "LIMIT_USAGE"],
    ),
    ScenarioItem(
        id="NT-006",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="신용등급 올라가면 알림 와?",
        description="GRADE_UP 트리거 알림 규칙 조회. 등급 상승 시 금리 인하 신청 안내 규칙 확인.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "신용등급", "GRADE_UP"],
    ),
    ScenarioItem(
        id="NT-007",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="APPLICATION",
        message="CUSTOMER_001에게 금리 변동 알림 보내줘",
        description="알림 발송 시나리오. MOCK_NOTIFICATION_SEND POST 호출 및 SENT 상태 반환 검증.",
        expected_concepts=["CONCEPT_NOTIFICATION"],
        expected_api="MOCK_NOTIFICATION_SEND",
        tags=["알림발송", "SEND", "CUSTOMER_001"],
    ),
    ScenarioItem(
        id="NT-008",
        category="notification",
        agent="NOTIFICATION_AGENT",
        intent="INQUIRY",
        message="대출 만기 됐을 때 알림 받을 수 있어?",
        description="만기 알림 가능 여부 문의. MATURITY 트리거 규칙 존재 여부 확인.",
        expected_concepts=["CONCEPT_NOTIFICATION", "CONCEPT_LOAN_STATUS"],
        expected_api="MOCK_NOTIFICATION_RULES",
        tags=["알림", "만기", "대출현황"],
    ),
    # ── 대출 상품 (loan) ────────────────────────────────────────
    ScenarioItem(
        id="LN-001",
        category="loan",
        agent="PRODUCT_AGENT",
        intent="INQUIRY",
        message="대출 상품 종류 알려줘",
        description="전체 대출 상품 목록 조회. MOCK_PRODUCT_LOOKUP 호출 및 8개 상품 확인.",
        expected_concepts=["CONCEPT_LOAN_PRODUCT"],
        expected_api="MOCK_PRODUCT_LOOKUP",
        tags=["대출상품", "목록"],
    ),
    ScenarioItem(
        id="LN-002",
        category="loan",
        agent="PRODUCT_AGENT",
        intent="RECOMMENDATION",
        message="직장인인데 신용대출 추천해줘",
        description="직장인 신용대출 추천. RECOMMENDATION 의도 탐지 검증.",
        expected_concepts=["CONCEPT_PERSONAL_CREDIT_LOAN", "CONCEPT_LOAN_PRODUCT"],
        expected_api="MOCK_PRODUCT_LOOKUP",
        tags=["추천", "직장인", "신용대출"],
    ),
    # ── 금리 (rate) ─────────────────────────────────────────────
    ScenarioItem(
        id="RT-001",
        category="rate",
        agent="RATE_AGENT",
        intent="INQUIRY",
        message="신용대출 금리 얼마야?",
        description="신용대출 금리 조회. MOCK_RATE_LOOKUP 호출 및 금리 범위 확인.",
        expected_concepts=["CONCEPT_INTEREST_RATE", "CONCEPT_PERSONAL_CREDIT_LOAN"],
        expected_api="MOCK_RATE_LOOKUP",
        tags=["금리", "신용대출"],
    ),
    ScenarioItem(
        id="RT-002",
        category="rate",
        agent="RATE_AGENT",
        intent="INQUIRY",
        message="3등급이면 금리 얼마야?",
        description="신용등급 3등급 맞춤 금리 조회. MOCK_PERSONALIZED_RATE_LOOKUP 호출 및 등급 파라미터 추출 검증.",
        expected_concepts=["CONCEPT_INTEREST_RATE"],
        expected_api="MOCK_PERSONALIZED_RATE_LOOKUP",
        tags=["신용등급", "맞춤금리", "3등급"],
    ),
    ScenarioItem(
        id="RT-003",
        category="rate",
        agent="RATE_AGENT",
        intent="INQUIRY",
        message="3천만원 5% 36개월 월 납입금 얼마야?",
        description="월 상환금 시뮬레이션. MOCK_RATE_SIMULATION 파라미터 추출(원금/금리/기간) 검증.",
        expected_concepts=["CONCEPT_INTEREST_RATE"],
        expected_api="MOCK_RATE_SIMULATION",
        tags=["시뮬레이션", "월납입금", "계산"],
    ),
]

# 카테고리 마스터 목록
_ALL_CATEGORIES = sorted({s.category for s in _SCENARIOS})


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_analyst_context),
):
    request_id = str(uuid4())
    timer = Timer()

    owner_name = body.user_id or auth.name

    record_event(
        db,
        request_id=request_id,
        event_type="REQUEST_RECEIVED",
        input_data={
            "message": body.message,
            "session_id": body.session_id,
            "channel": body.channel,
            "user_id": owner_name,
        },
    )

    leader = LeaderAgent()
    result = await leader.run(
        db=db,
        request_id=request_id,
        message=body.message,
        session_id=body.session_id,
        owner_name=owner_name,
        owner_role=auth.role.value,
    )

    record_event(
        db,
        request_id=request_id,
        event_type="RESPONSE_COMPLETED",
        output_data={
            "answer_length": len(result.answer),
            "intent": result.intent.get("intent"),
            "memory_turns": result.memory_turns,
        },
        duration_ms=timer.elapsed_ms(),
    )

    return ChatResponse(
        request_id=request_id,
        message=body.message,
        plan=result.plan,
        results=result.ranked_results,
        answer=result.answer,
        intent=result.intent,
        memory_turns=result.memory_turns,
        trace_count=count_events(db, request_id),
        evidence_count=count_evidence(db, request_id),
        decision_v2=result.decision_v2,
        needs_clarification=result.needs_clarification,
        clarification_question=result.clarification_question,
    )


@router.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios(
    category: str | None = Query(default=None, description="카테고리 필터 (forex / notification / loan / rate)"),
    agent: str | None = Query(default=None, description="Agent ID 필터 (예: FOREX_AGENT)"),
    intent: str | None = Query(default=None, description="의도 유형 필터 (INQUIRY / COMPARISON / RECOMMENDATION / APPLICATION)"),
    tag: str | None = Query(default=None, description="태그 키워드 필터 (예: 달러, 환전)"),
):
    """
    사전 정의된 Chat 테스트 시나리오 목록을 반환합니다.

    query parameter로 카테고리·에이전트·의도·태그를 조합해 필터링할 수 있습니다.
    반환된 `message` 필드를 `/api/v1/ai/chat`의 `message`에 그대로 사용하면
    해당 시나리오를 테스트할 수 있습니다.
    """
    result = _SCENARIOS

    if category:
        result = [s for s in result if s.category == category.lower()]
    if agent:
        result = [s for s in result if s.agent == agent.upper()]
    if intent:
        result = [s for s in result if s.intent == intent.upper()]
    if tag:
        result = [s for s in result if tag in s.tags]

    categories = sorted({s.category for s in result}) if result else _ALL_CATEGORIES

    return ScenarioListResponse(
        total=len(result),
        categories=categories,
        scenarios=result,
    )
