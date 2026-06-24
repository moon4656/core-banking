from app.agents.leader import LeaderAgent
from app.schemas.ai_gateway import StepResult
import pytest


def test_validate_structured_answer_accepts_grounded_numeric_bullets():
    agent = LeaderAgent()
    results = [
        StepResult(
            api_id="MOCK_RATE_SIMULATION",
            status="success",
            data={
                "principal": 30_000_000,
                "annual_rate": 8.0,
                "term_months": 24,
                "method": "거치식원금균등상환",
                "grace_months": 5,
                "grace_monthly_interest": 200_000,
                "first_repay_payment": 1_778_947,
                "last_repay_payment": 1_589_473,
                "total_interest": 2_999_991,
                "total_payment": 32_999_991,
            },
            error=None,
        )
    ]

    payload = {
        "summary": "금리 시뮬레이션 결과입니다.",
        "bullets": [
            {
                "text": "대출원금 30,000,000원 / 연 8.0% / 24개월",
                "source_api_id": "MOCK_RATE_SIMULATION",
            },
            {
                "text": "총 이자: 2,999,991원",
                "source_api_id": "MOCK_RATE_SIMULATION",
            },
        ],
        "missing_information": [],
        "disclaimer": "안내용 결과입니다.",
    }

    normalized = agent._validate_structured_answer_payload(payload, results)

    assert normalized is not None
    assert normalized["bullets"][1]["text"] == "총 이자: 2,999,991원"


def test_validate_structured_answer_rejects_ungrounded_numeric_bullets():
    agent = LeaderAgent()
    results = [
        StepResult(
            api_id="MOCK_PRODUCT_LOOKUP",
            status="success",
            data={
                "products": [
                    {
                        "name": "직장인 신용대출",
                        "min_rate": 4.5,
                        "max_rate": 9.8,
                    }
                ]
            },
            error=None,
        )
    ]

    payload = {
        "summary": "조회 결과입니다.",
        "bullets": [
            {
                "text": "총 이자: 2,999,991원",
                "source_api_id": "MOCK_PRODUCT_LOOKUP",
            }
        ],
        "missing_information": [],
        "disclaimer": "안내용 결과입니다.",
    }

    normalized = agent._validate_structured_answer_payload(payload, results)

    assert normalized is None


def test_render_structured_answer_formats_sections():
    agent = LeaderAgent()
    payload = {
        "summary": "시뮬레이션 결과입니다.",
        "bullets": [
            {
                "text": "대출원금 30,000,000원 / 연 8.0% / 24개월",
                "source_api_id": "MOCK_RATE_SIMULATION",
            },
            {
                "text": "총 이자: 2,999,991원",
                "source_api_id": "MOCK_RATE_SIMULATION",
            },
        ],
        "missing_information": ["월 납입금은 응답 데이터에 없어 안내하지 않습니다."],
        "disclaimer": "실제 상품 조건은 영업점 또는 공식 앱에서 확인해 주세요.",
    }

    answer = agent._render_structured_answer(payload)

    assert "시뮬레이션 결과입니다." in answer
    assert "- 대출원금 30,000,000원 / 연 8.0% / 24개월" in answer
    assert "- 총 이자: 2,999,991원" in answer
    assert "Missing information" in answer
    assert "월 납입금은 응답 데이터에 없어 안내하지 않습니다." in answer


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _QueuedCompletions:
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.calls = 0
        self.last_messages = []

    async def create(self, **kwargs):
        self.calls += 1
        self.last_messages = kwargs.get("messages", [])
        index = min(self.calls - 1, len(self._responses) - 1)
        return _FakeResponse(self._responses[index])


class _FakeClient:
    def __init__(self, responses: list[str]):
        self.chat = type("FakeChat", (), {"completions": _QueuedCompletions(responses)})()


@pytest.mark.asyncio
async def test_summarize_retries_once_when_structured_payload_is_invalid(monkeypatch):
    agent = LeaderAgent()
    agent._llm_enabled = True
    responses = [
        '{"summary":"조회 결과입니다.","bullets":[{"text":"총 이자: 2,999,991원","source_api_id":"MOCK_PRODUCT_LOOKUP"}],"missing_information":[],"disclaimer":"안내용"}',
        '{"summary":"조회 결과입니다.","bullets":[{"text":"직장인 신용대출 4.5% ~ 9.8%","source_api_id":"MOCK_RATE_LOOKUP"}],"missing_information":[],"disclaimer":"안내용"}',
    ]
    fake_client = _FakeClient(responses)

    monkeypatch.setattr("app.agents.leader.AsyncOpenAI", lambda api_key=None: fake_client)

    results = [
        StepResult(
            api_id="MOCK_PRODUCT_LOOKUP",
            status="success",
            data={"products": [{"name": "직장인 신용대출", "min_rate": 4.5, "max_rate": 9.8}]},
            error=None,
        ),
        StepResult(
            api_id="MOCK_RATE_LOOKUP",
            status="success",
            data={"rates": [{"product_name": "직장인 신용대출", "min_final_rate": "4.5", "max_final_rate": "9.8"}]},
            error=None,
        ),
    ]

    answer = await agent._summarize(
        message="직장인 신용대출 조건 알려줘",
        intent_data={"intent": "INQUIRY"},
        history=[],
        ranked_results=results,
        ltm_history=None,
        db=None,
    )

    assert fake_client.chat.completions.calls == 2
    assert "- 직장인 신용대출 4.5% ~ 9.8%" in answer


@pytest.mark.asyncio
async def test_summarize_falls_back_to_template_after_retry_failure(monkeypatch):
    agent = LeaderAgent()
    agent._llm_enabled = True
    responses = [
        '{"summary":"조회 결과입니다.","bullets":[{"text":"총 이자: 2,999,991원","source_api_id":"MOCK_PRODUCT_LOOKUP"}],"missing_information":[],"disclaimer":"안내용"}',
        '{"summary":"조회 결과입니다.","bullets":[{"text":"월 납입금: 0원","source_api_id":"MOCK_PRODUCT_LOOKUP"}],"missing_information":[],"disclaimer":"안내용"}',
    ]
    fake_client = _FakeClient(responses)

    monkeypatch.setattr("app.agents.leader.AsyncOpenAI", lambda api_key=None: fake_client)
    monkeypatch.setattr(agent, "_template_answer", lambda results: "TEMPLATE_FALLBACK")

    results = [
        StepResult(
            api_id="MOCK_PRODUCT_LOOKUP",
            status="success",
            data={"products": [{"name": "직장인 신용대출", "min_rate": 4.5, "max_rate": 9.8}]},
            error=None,
        ),
        StepResult(
            api_id="MOCK_RATE_LOOKUP",
            status="success",
            data={"rates": [{"product_name": "직장인 신용대출", "min_final_rate": "4.5", "max_final_rate": "9.8"}]},
            error=None,
        ),
    ]

    answer = await agent._summarize(
        message="직장인 신용대출 조건 알려줘",
        intent_data={"intent": "INQUIRY"},
        history=[],
        ranked_results=results,
        ltm_history=None,
        db=None,
    )

    assert fake_client.chat.completions.calls == 2
    assert answer == "TEMPLATE_FALLBACK"
