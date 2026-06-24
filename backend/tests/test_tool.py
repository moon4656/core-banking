# test_tool.py — Tool/API Hub 호출 기능 테스트
#
# tool_gateway.py의 invoke_tool 함수를 검증한다.
#
# [Mock 사용 이유]
#   invoke_tool은 httpx로 외부 Mock API를 호출한다.
#   테스트 환경에서 Mock API 컨테이너가 항상 준비된다는 보장이 없으므로,
#   unittest.mock.patch로 httpx.AsyncClient를 가로채 가상 응답을 반환한다.
#   이렇게 하면 네트워크 없이도 Tool Hub 로직 자체를 검증할 수 있다.
#
# [실제 네트워크 테스트]
#   컨테이너 내부에서 mock-api:8010이 실행 중이라면 mock 없이도 테스트 가능하다.
#   test_chat.py 에서는 mock 없이 실제 네트워크로 통합 테스트한다.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.trace_model import ToolExecutionTrace
from app.tools.tool_gateway import invoke_tool


@pytest.mark.asyncio
async def test_invoke_valid_tool_mocked(db):
    """
    MOCK_PRODUCT_LOOKUP을 호출하면 Mock API의 상품 목록을 반환해야 한다.
    httpx.AsyncClient.get을 가로채 가짜 응답을 반환한다.
    """
    # Mock API가 반환할 가짜 JSON 응답
    fake_response_data = {"products": [{"product_id": "P001", "name": "테스트대출"}], "total": 1}

    # httpx.AsyncClient 전체를 mock으로 교체
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_response_data
    mock_resp.raise_for_status = MagicMock()  # 예외 없이 통과

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    # AsyncClient를 context manager로 사용하므로 __aenter__ 반환값 설정
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.tools.tool_gateway.httpx.AsyncClient", return_value=mock_client):
        result = await invoke_tool(db, "MOCK_PRODUCT_LOOKUP", {})

    assert result.status == "success"
    assert result.data is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_invoke_invalid_tool(db):
    """
    존재하지 않는 api_id를 전달하면 status=error를 반환해야 한다.
    Tool Hub는 예외를 전파하지 않고 error 상태로 감싸서 반환한다.
    이렇게 하면 한 Tool 실패가 전체 Orchestrator 실행을 중단시키지 않는다.
    """
    result = await invoke_tool(db, "NONEXISTENT_TOOL_ID", {})

    assert result.status == "error"
    assert result.data is None
    assert result.error is not None
    assert "NONEXISTENT_TOOL_ID" in result.error


# ── Phase 4 테스트 ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invoke_tool_returns_latency_ms(db):
    """
    invoke_tool()은 HTTP 호출 latency_ms를 ToolInvokeResponse에 담아 반환해야 한다.
    성공·실패 모두 latency_ms가 0 이상의 정수여야 한다.
    """
    fake_data = {"products": [{"product_id": "P001"}], "total": 1}

    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_data
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.tools.tool_gateway.httpx.AsyncClient", return_value=mock_client):
        result = await invoke_tool(db, "MOCK_PRODUCT_LOOKUP", {})

    assert result.status == "success"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_invoke_tool_returns_output_masked(db):
    """
    invoke_tool()은 민감 필드를 마스킹한 output_masked를 반환해야 한다.
    credit_score, income 같은 PII 키는 '***'로 대체돼야 한다.
    """
    fake_data = {
        "product_name": "신용대출 A",
        "rate": 4.5,
        "credit_score": 750,
        "income": 50000000,
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_data
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.tools.tool_gateway.httpx.AsyncClient", return_value=mock_client):
        result = await invoke_tool(db, "MOCK_PRODUCT_LOOKUP", {})

    assert result.output_masked is not None
    assert result.output_masked.get("product_name") == "신용대출 A"
    assert result.output_masked.get("rate") == 4.5
    assert result.output_masked.get("credit_score") == "***"
    assert result.output_masked.get("income") == "***"


def test_tool_execution_trace_saved_after_chat(auth_client, db):
    """
    Chat 요청 1건 처리 후 ai_tool_execution에 Tool 실행 레코드가 저장돼야 한다.
    latency_ms가 0 이상으로 기록되고, status='success' 레코드가 있어야 한다.
    """
    chat_resp = auth_client.post(
        "/api/v1/ai/chat",
        headers={"X-API-Key": "test-analyst-key"},
        json={"message": "신용대출 금리 알려줘", "session_id": "p4-tool-trace-001"},
    )
    assert chat_resp.status_code == 200
    request_id = chat_resp.json()["request_id"]

    rows = (
        db.query(ToolExecutionTrace)
        .filter(ToolExecutionTrace.request_id == request_id)
        .all()
    )

    assert rows, "ai_tool_execution에 레코드가 없음"
    assert any(r.status == "success" for r in rows), "성공 레코드가 없음"
    assert all(r.latency_ms is not None and r.latency_ms >= 0 for r in rows), (
        "latency_ms가 None이거나 음수인 레코드 있음"
    )
