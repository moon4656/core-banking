# search_agent.py — 서류 검색 및 상담 이력 전담 Sub Agent
#
# [담당 Concept]
#   CONCEPT_REQUIRED_DOCUMENT : 대출 종류·고객 유형별 제출 서류
#   CONCEPT_COUNSELING_HISTORY: 고객 과거 상담 이력
#
# [사용 Tool]
#   MOCK_DOCUMENT_SEARCH    : 필요서류 키워드 검색
#   MOCK_COUNSELING_HISTORY : 상담 이력 조회 (customer_id 없으면 전체 반환)
#
# [run() 오버라이드 이유]
#   MOCK_DOCUMENT_SEARCH 에 의도 키워드를 params로 전달해 검색 정확도를 높인다.
#   다른 API는 super().run()과 동일하게 처리한다.

from sqlalchemy.orm import Session

from app.agents.base_agent import AbstractAgent, AgentInput, AgentOutput
from app.tools.tool_gateway import invoke_tool
from app.trace.trace_service import Timer


class SearchAgent(AbstractAgent):
    """서류 검색, 상담 이력, 영업점 정보를 조회하는 Sub Agent."""

    @property
    def agent_id(self) -> str:
        return "SEARCH_AGENT"

    async def run(self, db: Session, input: AgentInput) -> AgentOutput:
        # 의도 키워드가 있으면 서류 검색에 활용
        keyword = " ".join(input.intent.get("keywords", []))

        api_results: list[dict] = []
        for api_id in input.api_ids:
            params = {"keyword": keyword} if (api_id == "MOCK_DOCUMENT_SEARCH" and keyword) else {}
            t = Timer()
            result = await invoke_tool(db, api_id, params=params)
            api_results.append({
                "api_id":     api_id,
                "status":     result.status,
                "data":       result.data,
                "error":      result.error,
                "latency_ms": t.elapsed_ms(),
            })

        success_count = sum(1 for r in api_results if r["status"] == "success")
        confidence = success_count / len(api_results) if api_results else 0.0

        return AgentOutput(
            agent_id=self.agent_id,
            api_results=api_results,
            confidence=confidence,
            metadata={
                "processed_apis": len(api_results),
                "used_keyword":   bool(keyword),
            },
        )
