# base_agent.py — 모든 Sub Agent가 상속해야 하는 추상 기반 클래스
#
# [왜 추상 클래스가 필요한가?]
#   Leader Agent는 어떤 Sub Agent를 호출하든 같은 방식으로 입력을 주고 결과를 받는다.
#   추상 클래스(AbstractAgent)를 정의하면:
#     1. 모든 Sub Agent가 동일한 메서드 시그니처를 강제로 구현해야 한다 (계약)
#     2. Leader Agent는 구체 클래스를 알 필요 없이 AbstractAgent 타입으로만 다룬다
#     3. 새 Sub Agent를 추가할 때 어떤 메서드를 구현해야 하는지 명확하다
#
# [입출력 표준]
#   AgentInput  : Leader Agent → Sub Agent 로 전달하는 표준 입력 객체
#   AgentOutput : Sub Agent → Leader Agent 로 반환하는 표준 출력 객체
#
# [사용 예시]
#   class ProductAgent(AbstractAgent):
#       async def run(self, input: AgentInput) -> AgentOutput:
#           ...  # 구현
#
#   agent = ProductAgent()
#   output = await agent.run(AgentInput(message="신용대출 알려줘", ...))
#   print(output.answer, output.raw_data)

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class AgentInput:
    """
    Leader Agent가 Sub Agent에게 전달하는 표준 입력.

    Attributes:
        message       : 사용자 원본 질문 (전체 맥락 파악 용도)
        intent        : Leader Agent가 분석한 의도 (예: {"intent": "INQUIRY"})
        concept_ids   : 이 Agent가 처리해야 할 concept ID 목록
                        (예: ["CONCEPT_INTEREST_RATE", "CONCEPT_PREFERENTIAL_RATE"])
        api_ids       : 호출해야 할 Tool(API) ID 목록
                        (예: ["MOCK_RATE_LOOKUP", "MOCK_RATE_SIMULATION"])
        session_id    : Redis Short Memory 조회용 세션 ID
        request_id    : Trace 기록용 요청 고유 ID
    """
    message:     str
    intent:      dict
    concept_ids: list[str]
    api_ids:     list[str]
    session_id:  str
    request_id:  str


@dataclass
class AgentOutput:
    """
    Sub Agent가 Leader Agent에게 반환하는 표준 출력.

    Attributes:
        agent_id    : 이 결과를 생성한 Agent ID (예: "PRODUCT_AGENT")
        api_results : Tool 호출 결과 목록. 각 항목은 {"api_id": ..., "data": ..., "status": ...}
        answer      : Sub Agent가 생성한 중간 답변 (선택적 — 최종 요약은 Leader가 담당)
        confidence  : 결과 신뢰도 점수 (0.0 ~ 1.0). Re-ranking 에 활용된다.
        metadata    : 추가 디버그 정보 (툴 호출 시간, 오류 메시지 등)
    """
    agent_id:    str
    api_results: list[dict]
    answer:      str       = ""
    confidence:  float     = 1.0
    metadata:    dict      = field(default_factory=dict)


class AbstractAgent(ABC):
    """
    모든 Sub Agent가 상속해야 하는 추상 기반 클래스.

    [구현 의무]
        - agent_id property : 각 Sub Agent의 고유 ID 반환

    [선택 재정의]
        - run() : 기본 구현은 input.api_ids를 순회하며 params={} 로 Tool Hub를 호출한다.
                  특수 파라미터나 메타데이터가 필요한 Agent는 오버라이드한다.
                  오버라이드 시 super().run()을 호출해 기본 흐름을 재사용할 수 있다.

    [latency 기록]
        기본 run()은 각 invoke_tool 호출마다 Timer로 실제 latency를 측정해
        api_results[*]["latency_ms"] 에 기록한다.
        leader.py는 이 값을 Evidence 신뢰도 계산에 활용한다.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """이 Agent의 고유 식별자. DB agent_catalog.agent_id 와 일치해야 한다."""

    async def run(self, db: "Session", input: AgentInput) -> AgentOutput:
        """
        기본 실행: api_ids를 순회하며 params={} 로 Tool Hub를 호출한다.

        각 API 호출의 실제 응답 시간(latency_ms)을 측정해 api_results에 포함한다.
        성공률로 confidence 점수를 계산한다.
        """
        from app.tools.tool_gateway import invoke_tool
        from app.trace.trace_service import Timer

        api_results: list[dict] = []
        for api_id in input.api_ids:
            t = Timer()
            result = await invoke_tool(db, api_id, params={})
            # invoke_tool()이 측정한 HTTP 순수 latency를 우선 사용; 없으면 외부 Timer fallback
            latency_ms = result.latency_ms if result.latency_ms is not None else t.elapsed_ms()
            api_results.append({
                "api_id":         api_id,
                "status":         result.status,
                "data":           result.data,
                "error":          result.error,
                "latency_ms":     latency_ms,
                "output_masked":  result.output_masked,
            })

        success_count = sum(1 for r in api_results if r["status"] == "success")
        confidence = success_count / len(api_results) if api_results else 0.0

        return AgentOutput(
            agent_id=self.agent_id,
            api_results=api_results,
            confidence=confidence,
            metadata={"processed_apis": len(api_results)},
        )
