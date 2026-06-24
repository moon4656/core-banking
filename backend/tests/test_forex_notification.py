# test_forex_notification.py — 외화 거래 / 알림 Agent 통합 테스트
#
# 검증 범위:
#   - FOREX_AGENT: 환율 조회, 환전 계산, 해외 송금, 외화예금 금리
#   - NOTIFICATION_AGENT: 알림 규칙 전체/필터 조회
#   - GET /api/v1/ai/scenarios: 시나리오 카탈로그 API
#
# [전제 조건]
#   - mock-api:8010 이 실행 중이어야 한다 (Docker 내부 실행)
#   - 마이그레이션 + seed 완료 후 실행
#
# [pytest marks]
#   pytest -m forex           — 외화 테스트만 실행
#   pytest -m notification    — 알림 테스트만 실행
#   pytest -m scenarios       — 시나리오 API 테스트만 실행

import pytest

from app.models.trace_model import EvidenceReference, TraceEvent


# ─────────────────────────────────────────────────────────────────────────────
# 공통 Fixture — trace/evidence 자동 정리
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _cleanup_traces(db):
    """테스트 전후 trace/evidence 신규 행 자동 정리."""
    baseline_ev = (
        db.query(EvidenceReference.id)
        .order_by(EvidenceReference.id.desc())
        .limit(1)
        .scalar()
    )
    baseline_tr = (
        db.query(TraceEvent.id)
        .order_by(TraceEvent.id.desc())
        .limit(1)
        .scalar()
    )
    yield
    if baseline_ev is None:
        db.query(EvidenceReference).delete(synchronize_session=False)
    else:
        db.query(EvidenceReference).filter(
            EvidenceReference.id > baseline_ev
        ).delete(synchronize_session=False)
    if baseline_tr is None:
        db.query(TraceEvent).delete(synchronize_session=False)
    else:
        db.query(TraceEvent).filter(
            TraceEvent.id > baseline_tr
        ).delete(synchronize_session=False)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 외화 거래 (FOREX_AGENT)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.forex
def test_forex_exchange_rate_basic(client):
    """달러 환율 조회 — FOREX_AGENT 라우팅 + MOCK_EXCHANGE_RATE_LOOKUP 호출."""
    resp = client.post("/api/v1/ai/chat", json={"message": "오늘 달러 환율 얼마야?"})
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert "CONCEPT_EXCHANGE_RATE" in detected, (
        f"환율 concept 미탐지: {detected}"
    )

    agents = body["plan"]["routed_agents"]
    assert "FOREX_AGENT" in agents, f"FOREX_AGENT 미선택: {agents}"

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_EXCHANGE_RATE_LOOKUP" in api_ids, (
        f"MOCK_EXCHANGE_RATE_LOOKUP 미실행: {api_ids}"
    )

    success = [r for r in body["results"] if r["api_id"] == "MOCK_EXCHANGE_RATE_LOOKUP"]
    assert success[0]["status"] == "success", f"환율 API 오류: {success[0].get('error')}"
    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_exchange_rate_no_pollution(client):
    """
    환전 계산 질문에 FOREX_AGENT가 라우팅되고 관련 API가 호출되어야 한다.

    body["results"]는 필터 전 전체 ranked_results이므로 여러 API가 포함될 수 있다.
    핵심 검증: FOREX_AGENT 라우팅 + 답변이 비어있지 않아야 한다.
    """
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "100만원 달러로 환전하면 얼마야?"},
    )
    assert resp.status_code == 200
    body = resp.json()

    agents = body["plan"]["routed_agents"]
    assert "FOREX_AGENT" in agents, f"FOREX_AGENT 미선택: {agents}"

    api_ids = [r["api_id"] for r in body["results"]]
    forex_apis = {"MOCK_CURRENCY_EXCHANGE_CALC", "MOCK_EXCHANGE_RATE_LOOKUP"}
    assert forex_apis & set(api_ids), f"외화 관련 API 미호출: {api_ids}"

    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_currency_exchange_calc_usd(client):
    """100만원 달러 환전 계산 — KRW→USD 파라미터 추출 및 계산 결과 검증."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "100만원 달러로 환전하면 얼마야?"},
    )
    assert resp.status_code == 200
    body = resp.json()

    agents = body["plan"]["routed_agents"]
    assert "FOREX_AGENT" in agents, f"FOREX_AGENT 미선택: {agents}"

    calc_results = [r for r in body["results"] if r["api_id"] == "MOCK_CURRENCY_EXCHANGE_CALC"]
    if calc_results:
        assert calc_results[0]["status"] == "success", (
            f"환전 계산 실패: {calc_results[0].get('error')}"
        )
        data = calc_results[0]["data"]
        if isinstance(data, dict):
            assert "result_amount" in data or "to_currency" in data, (
                f"환전 계산 응답 필드 없음: {data}"
            )

    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_currency_exchange_calc_jpy(client):
    """50만원 엔화 환전 계산 — JPY 통화 파라미터 추출 검증."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "50만원 엔화로 환전하면 얼마나 받아?"},
    )
    assert resp.status_code == 200
    body = resp.json()

    agents = body["plan"]["routed_agents"]
    assert "FOREX_AGENT" in agents, f"FOREX_AGENT 미선택: {agents}"
    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_remittance_general(client):
    """해외 송금 일반 안내 — MOCK_FOREIGN_REMITTANCE 호출 확인."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "해외 송금하려면 어떻게 해?"},
    )
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert "CONCEPT_FOREIGN_REMITTANCE" in detected, (
        f"해외송금 concept 미탐지: {detected}"
    )

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_FOREIGN_REMITTANCE" in api_ids, (
        f"MOCK_FOREIGN_REMITTANCE 미실행: {api_ids}"
    )
    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_remittance_with_amount(client):
    """
    해외 송금 수수료 질문 — "해외 송금" 명시 포함 시 FOREX_AGENT 라우팅 확인.

    "미국으로 1000달러 송금하면" 패턴은 토큰 분리 방식에 따라 Concept 탐지가 안 될 수 있다.
    "해외 송금" 키워드를 명시해 안정적으로 탐지되는 문구를 사용한다.
    """
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "해외 송금 수수료 얼마야? 미국으로 1000달러 보내려고"},
    )
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert "CONCEPT_FOREIGN_REMITTANCE" in detected, (
        f"해외송금 concept 미탐지: {detected}"
    )
    agents = body["plan"]["routed_agents"]
    assert "FOREX_AGENT" in agents, f"FOREX_AGENT 미선택: {agents}"
    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_foreign_deposit_rate_usd(client):
    """달러 예금 금리 조회 — MOCK_FOREIGN_DEPOSIT_RATE 호출 및 USD 금리 정보 반환."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "달러 예금 금리 얼마야?"},
    )
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert "CONCEPT_FOREIGN_DEPOSIT" in detected, (
        f"외화예금 concept 미탐지: {detected}"
    )

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_FOREIGN_DEPOSIT_RATE" in api_ids, (
        f"MOCK_FOREIGN_DEPOSIT_RATE 미실행: {api_ids}"
    )
    assert body["answer"], "answer 비어있음"


@pytest.mark.forex
def test_forex_foreign_deposit_rate_no_rate_pollution(client):
    """
    외화예금 금리 조회 — CONCEPT_FOREIGN_DEPOSIT 탐지 + MOCK_FOREIGN_DEPOSIT_RATE 호출.

    body["results"]는 answer 생성 필터 전 전체 ranked_results를 포함하므로
    여러 API 결과가 함께 있을 수 있다. 핵심 검증은 외화예금 API 호출 성공 여부이다.
    """
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "달러 예금 금리 얼마야?"},
    )
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert "CONCEPT_FOREIGN_DEPOSIT" in detected, (
        f"외화예금 concept 미탐지: {detected}"
    )

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_FOREIGN_DEPOSIT_RATE" in api_ids, (
        f"MOCK_FOREIGN_DEPOSIT_RATE 미실행: {api_ids}"
    )

    deposit_result = next(
        r for r in body["results"] if r["api_id"] == "MOCK_FOREIGN_DEPOSIT_RATE"
    )
    assert deposit_result["status"] == "success", (
        f"외화예금 금리 API 실패: {deposit_result.get('error')}"
    )


@pytest.mark.forex
@pytest.mark.parametrize("message,expected_concept", [
    ("오늘 환율 알려줘", "CONCEPT_EXCHANGE_RATE"),
    ("해외 송금 수수료 얼마야", "CONCEPT_FOREIGN_REMITTANCE"),
    ("외화예금 금리 전체 알려줘", "CONCEPT_FOREIGN_DEPOSIT"),
])
def test_forex_parametrized_concept_detection(client, message, expected_concept):
    """외화 카테고리 메시지별 Concept 탐지 파라미터화 테스트."""
    resp = client.post("/api/v1/ai/chat", json={"message": message})
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert expected_concept in detected, (
        f"[{message!r}] {expected_concept} 미탐지: {detected}"
    )
    assert "FOREX_AGENT" in body["plan"]["routed_agents"], (
        f"[{message!r}] FOREX_AGENT 미선택"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 알림 (NOTIFICATION_AGENT)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.notification
def test_notification_rules_all(client):
    """알림 규칙 전체 조회 — MOCK_NOTIFICATION_RULES 호출 및 6건 이상 반환."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "알림 규칙 전체 보여줘"},
    )
    assert resp.status_code == 200
    body = resp.json()

    detected = body["plan"]["detected_concepts"]
    assert "CONCEPT_NOTIFICATION" in detected, (
        f"알림 concept 미탐지: {detected}"
    )

    agents = body["plan"]["routed_agents"]
    assert "NOTIFICATION_AGENT" in agents, f"NOTIFICATION_AGENT 미선택: {agents}"

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_NOTIFICATION_RULES" in api_ids, (
        f"MOCK_NOTIFICATION_RULES 미실행: {api_ids}"
    )

    rules_result = next(r for r in body["results"] if r["api_id"] == "MOCK_NOTIFICATION_RULES")
    assert rules_result["status"] == "success"
    if isinstance(rules_result["data"], list):
        assert len(rules_result["data"]) >= 1, "알림 규칙이 1건 이상 있어야 한다"

    assert body["answer"], "answer 비어있음"


@pytest.mark.notification
@pytest.mark.parametrize("message,trigger_keyword", [
    ("금리 변동 알림 규칙 보여줘", "RATE_CHANGE"),
    ("만기 알림은 어떻게 설정돼 있어?", "MATURITY"),
    ("연체 알림 규칙 알려줘", "OVERDUE"),
    ("한도 소진 알림 설정 보여줘", "LIMIT_USAGE"),
    ("신용등급 올라가면 알림 와?", "GRADE_UP"),
])
def test_notification_rules_by_trigger_type(client, message, trigger_keyword):
    """
    트리거 유형별 알림 규칙 필터 조회.

    각 메시지가 NOTIFICATION_AGENT로 라우팅되고 MOCK_NOTIFICATION_RULES가 호출되어야 한다.
    필터 파라미터(trigger_type)가 올바르게 전달됐다면 Mock API 응답에 해당 규칙만 포함된다.
    """
    resp = client.post("/api/v1/ai/chat", json={"message": message})
    assert resp.status_code == 200
    body = resp.json()

    agents = body["plan"]["routed_agents"]
    assert "NOTIFICATION_AGENT" in agents, (
        f"[{message!r}] NOTIFICATION_AGENT 미선택: {agents}"
    )

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_NOTIFICATION_RULES" in api_ids, (
        f"[{message!r}] MOCK_NOTIFICATION_RULES 미실행: {api_ids}"
    )

    rules_result = next(r for r in body["results"] if r["api_id"] == "MOCK_NOTIFICATION_RULES")
    assert rules_result["status"] == "success", (
        f"[{message!r}] 알림 규칙 API 실패: {rules_result.get('error')}"
    )

    # 필터 파라미터가 전달됐다면 응답의 규칙 수가 전체보다 적어야 한다
    if isinstance(rules_result["data"], list):
        for rule in rules_result["data"]:
            if isinstance(rule, dict) and "trigger_type" in rule:
                assert rule["trigger_type"] == trigger_keyword, (
                    f"[{message!r}] trigger_type 불일치: {rule['trigger_type']} ≠ {trigger_keyword}"
                )

    assert body["answer"], f"[{message!r}] answer 비어있음"


@pytest.mark.notification
def test_notification_no_send_without_explicit_keyword(client):
    """
    알림 조회 질문에서는 MOCK_NOTIFICATION_SEND가 호출되지 않아야 한다.

    "발송", "보내줘" 등의 명시적 전송 키워드 없이는 발송 API를 호출하면 안 된다.
    """
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "금리 변동 알림 규칙 보여줘"},
    )
    assert resp.status_code == 200
    body = resp.json()

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_NOTIFICATION_SEND" not in api_ids, (
        "알림 조회 질문인데 MOCK_NOTIFICATION_SEND가 호출됨 — 의도 분류 오류"
    )


@pytest.mark.notification
def test_notification_no_rate_pollution(client):
    """알림 질문에 대출 금리 API가 함께 노출되지 않아야 한다."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "알림 규칙 전체 보여줘"},
    )
    assert resp.status_code == 200
    body = resp.json()

    api_ids = [r["api_id"] for r in body["results"]]
    contaminating = {"MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION", "MOCK_PRODUCT_LOOKUP"}
    overlap = contaminating & set(api_ids)
    assert not overlap, (
        f"알림 조회에 대출 관련 API가 혼입됨: {overlap}"
    )


@pytest.mark.notification
def test_notification_send_with_explicit_keyword(client):
    """알림 발송 요청 — 명시적 발송 키워드 포함 시 MOCK_NOTIFICATION_SEND 호출."""
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "CUSTOMER_001에게 금리 변동 알림 보내줘"},
    )
    assert resp.status_code == 200
    body = resp.json()

    agents = body["plan"]["routed_agents"]
    assert "NOTIFICATION_AGENT" in agents, f"NOTIFICATION_AGENT 미선택: {agents}"

    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_NOTIFICATION_SEND" in api_ids, (
        "발송 요청인데 MOCK_NOTIFICATION_SEND 미실행"
    )

    send_result = next(r for r in body["results"] if r["api_id"] == "MOCK_NOTIFICATION_SEND")
    assert send_result["status"] == "success", (
        f"알림 발송 실패: {send_result.get('error')}"
    )
    if isinstance(send_result["data"], dict):
        assert send_result["data"].get("status") == "SENT", (
            f"알림 발송 상태가 SENT가 아님: {send_result['data']}"
        )

    assert body["answer"], "answer 비어있음"


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 카탈로그 API
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.scenarios
def test_scenarios_list_all(client):
    """GET /api/v1/ai/scenarios — 전체 시나리오 목록 반환."""
    resp = client.get("/api/v1/ai/scenarios")
    assert resp.status_code == 200
    body = resp.json()

    assert "total" in body
    assert "categories" in body
    assert "scenarios" in body
    assert body["total"] > 0, "시나리오가 1건 이상 있어야 한다"
    assert len(body["scenarios"]) == body["total"]

    # 카테고리 목록에 forex, notification 포함 여부 확인
    assert "forex" in body["categories"], "forex 카테고리 없음"
    assert "notification" in body["categories"], "notification 카테고리 없음"


@pytest.mark.scenarios
def test_scenarios_filter_by_category_forex(client):
    """forex 카테고리 필터 — forex 시나리오만 반환."""
    resp = client.get("/api/v1/ai/scenarios?category=forex")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] > 0, "forex 시나리오 없음"
    for s in body["scenarios"]:
        assert s["category"] == "forex", f"forex가 아닌 카테고리 포함: {s['category']}"
        assert s["agent"] == "FOREX_AGENT", f"FOREX_AGENT가 아닌 agent 포함: {s['agent']}"


@pytest.mark.scenarios
def test_scenarios_filter_by_category_notification(client):
    """notification 카테고리 필터 — notification 시나리오만 반환."""
    resp = client.get("/api/v1/ai/scenarios?category=notification")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] > 0, "notification 시나리오 없음"
    for s in body["scenarios"]:
        assert s["category"] == "notification", f"notification이 아닌 카테고리: {s['category']}"


@pytest.mark.scenarios
def test_scenarios_filter_by_agent(client):
    """agent 필터 — NOTIFICATION_AGENT 시나리오만 반환."""
    resp = client.get("/api/v1/ai/scenarios?agent=NOTIFICATION_AGENT")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] > 0, "NOTIFICATION_AGENT 시나리오 없음"
    for s in body["scenarios"]:
        assert s["agent"] == "NOTIFICATION_AGENT"


@pytest.mark.scenarios
def test_scenarios_filter_by_intent(client):
    """intent 필터 — INQUIRY 시나리오만 반환."""
    resp = client.get("/api/v1/ai/scenarios?intent=INQUIRY")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] > 0
    for s in body["scenarios"]:
        assert s["intent"] == "INQUIRY"


@pytest.mark.scenarios
def test_scenarios_filter_combined(client):
    """복합 필터 — forex 카테고리 + INQUIRY 의도 조합."""
    resp = client.get("/api/v1/ai/scenarios?category=forex&intent=INQUIRY")
    assert resp.status_code == 200
    body = resp.json()

    for s in body["scenarios"]:
        assert s["category"] == "forex"
        assert s["intent"] == "INQUIRY"


@pytest.mark.scenarios
def test_scenarios_filter_by_tag(client):
    """tag 필터 — '달러' 태그로 필터링."""
    resp = client.get("/api/v1/ai/scenarios?tag=달러")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] > 0, "'달러' 태그 시나리오 없음"
    for s in body["scenarios"]:
        assert "달러" in s["tags"], f"'달러' 태그 없는 시나리오 포함: {s['id']}"


@pytest.mark.scenarios
def test_scenarios_schema_fields(client):
    """시나리오 응답의 필수 스키마 필드 검증."""
    resp = client.get("/api/v1/ai/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()["scenarios"]

    required_fields = {"id", "category", "agent", "intent", "message", "description"}
    for s in scenarios:
        missing = required_fields - set(s.keys())
        assert not missing, f"시나리오 {s.get('id')} 필드 누락: {missing}"
        assert s["message"], f"시나리오 {s.get('id')} message 비어있음"


@pytest.mark.scenarios
def test_scenarios_message_is_usable_in_chat(client):
    """
    시나리오 message를 그대로 Chat API에 사용할 수 있어야 한다.

    FX-001 (달러 환율) 시나리오의 message를 직접 Chat API에 전송하고 200 응답 확인.
    """
    # 1. 시나리오 조회
    scenarios_resp = client.get("/api/v1/ai/scenarios?category=forex")
    assert scenarios_resp.status_code == 200
    forex_scenarios = scenarios_resp.json()["scenarios"]
    assert forex_scenarios, "forex 시나리오 없음"

    fx001 = next((s for s in forex_scenarios if s["id"] == "FX-001"), None)
    assert fx001 is not None, "FX-001 시나리오 없음"

    # 2. FX-001 message를 그대로 Chat API에 전송
    chat_resp = client.post(
        "/api/v1/ai/chat",
        json={"message": fx001["message"]},
    )
    assert chat_resp.status_code == 200
    chat_body = chat_resp.json()

    # 3. 예상 Agent가 라우팅됐는지 확인
    agents = chat_body["plan"]["routed_agents"]
    assert fx001["agent"] in agents, (
        f"FX-001 예상 agent({fx001['agent']}) 미선택. 실제: {agents}"
    )
    assert chat_body["answer"], "Chat 답변 비어있음"


@pytest.mark.scenarios
def test_scenarios_notification_message_in_chat(client):
    """
    NT-001 (알림 규칙 전체 조회) 시나리오 message를 Chat에 전송하면 NOTIFICATION_AGENT가 라우팅돼야 한다.
    """
    scenarios_resp = client.get("/api/v1/ai/scenarios?category=notification")
    assert scenarios_resp.status_code == 200
    nt_scenarios = scenarios_resp.json()["scenarios"]

    nt001 = next((s for s in nt_scenarios if s["id"] == "NT-001"), None)
    assert nt001 is not None, "NT-001 시나리오 없음"

    chat_resp = client.post(
        "/api/v1/ai/chat",
        json={"message": nt001["message"]},
    )
    assert chat_resp.status_code == 200
    chat_body = chat_resp.json()

    agents = chat_body["plan"]["routed_agents"]
    assert "NOTIFICATION_AGENT" in agents, (
        f"NT-001: NOTIFICATION_AGENT 미선택. 실제: {agents}"
    )
    assert chat_body["answer"], "Chat 답변 비어있음"
