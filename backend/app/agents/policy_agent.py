# policy_agent.py — 여신 정책 및 약관 전담 Sub Agent
#
# [담당 Concept]
#   CONCEPT_POLICY: 신용심사 기준, LTV/DSR 한도, 중도상환수수료, 연체정책
#   CONCEPT_TERMS : 약관, 동의서, 규정 문서
#
# [사용 Tool]
#   MOCK_POLICY_LOOKUP: 정책/약관 목록 조회
#
# [run() 오버라이드 이유]
#   APPLICATION 의도일 때 is_application=True 를 metadata에 추가해
#   Leader Agent re-ranking 시 정책 데이터를 우선 처리하도록 힌트를 제공한다.

from sqlalchemy.orm import Session

from app.agents.base_agent import AbstractAgent, AgentInput, AgentOutput


class PolicyAgent(AbstractAgent):
    """여신 정책, 약관, 규정 정보를 조회하는 Sub Agent."""

    @property
    def agent_id(self) -> str:
        return "POLICY_AGENT"

    async def run(self, db: Session, input: AgentInput) -> AgentOutput:
        output = await super().run(db, input)
        output.metadata["is_application"] = input.intent.get("intent") == "APPLICATION"
        return output
