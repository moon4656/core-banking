# product_agent.py — 대출 상품 및 신청 조건 전담 Sub Agent
#
# [담당 Concept]
#   CONCEPT_LOAN_PRODUCT        : 전체 대출 상품 목록/조건
#   CONCEPT_PERSONAL_CREDIT_LOAN: 신용대출 특화 정보
#   CONCEPT_CUSTOMER            : 고객 유형별 상품 조건
#   CONCEPT_APPLICATION_CONDITION: 신청 자격 및 한도 조건
#
# [사용 Tool]
#   MOCK_PRODUCT_LOOKUP   : 상품 목록 조회
#   MOCK_ELIGIBILITY_CHECK: 신청 자격 사전 확인 (DSR, 신용점수 기준)
#
# [run() 구현]
#   AbstractAgent.run() 기본 구현을 그대로 사용한다.
#   params={} 로 전체 데이터 조회 — 특수 파라미터 불필요.

from app.agents.base_agent import AbstractAgent


class ProductAgent(AbstractAgent):
    """대출 상품 정보를 조회하는 Sub Agent."""

    @property
    def agent_id(self) -> str:
        return "PRODUCT_AGENT"

    # run()은 AbstractAgent 기본 구현 사용:
    # api_ids 순회 → invoke_tool(params={}) → latency 측정 → AgentOutput 반환
