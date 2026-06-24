from app.agents.leader import LeaderAgent
from app.schemas.ai_gateway import StepResult


def test_single_result_answer_formats_grace_equal_principal_simulation():
    agent = LeaderAgent()
    result = StepResult(
        api_id="MOCK_RATE_SIMULATION",
        status="success",
        data={
            "principal": 30_000_000,
            "annual_rate": 8.0,
            "term_months": 24,
            "method": "거치식원금균등상환",
            "grace_months": 5,
            "grace_monthly_interest": 200_000,
            "repay_months": 19,
            "monthly_principal": 1_578_947,
            "first_repay_payment": 1_778_947,
            "last_repay_payment": 1_589_473,
            "total_payment": 32_999_991,
            "total_interest": 2_999_991,
        },
        error=None,
    )

    answer = agent._single_result_answer(result, "내가 직장인 신용대출 최고이율 2년 5개월 거치 원금균등상환 예측 해줘")

    assert "월 납입금: 0원" not in answer
    assert "거치 기간 5개월" in answer
    assert "월 이자 200,000원" in answer
    assert "첫달 1,778,947원" in answer
    assert "마지막달 1,589,473원" in answer
