# notification_agent.py — 알림 규칙 조회 및 발송 Sub Agent
#
# [담당 Concept]
#   CONCEPT_NOTIFICATION : 알림 규칙 조회, 알림 발송
#   CONCEPT_LOAN_STATUS  : 대출 만기·연체 등 현황 기반 알림
#
# [사용 Tool]
#   MOCK_NOTIFICATION_RULES : 알림 규칙 목록 조회
#   MOCK_NOTIFICATION_SEND  : 알림 발송 (POST)
#
# [특수 동작]
#   사용자 메시지에 "발송", "보내줘", "알려줘" 등 액션 키워드가 없으면
#   MOCK_NOTIFICATION_RULES만 호출(조회)하고 SEND는 건너뛴다.

import re

from sqlalchemy.orm import Session

from app.agents.base_agent import AbstractAgent, AgentInput, AgentOutput

_SEND_KEYWORDS = ["발송", "보내줘", "보내", "알림 보내", "알려줘", "알림 줘", "send"]
_TRIGGER_TYPE_MAP = {
    "금리":   "RATE_CHANGE",
    "만기":   "MATURITY",
    "연체":   "OVERDUE",
    "한도":   "LIMIT_USAGE",
    "등급":   "GRADE_UP",
}


def _wants_send(message: str) -> bool:
    return any(kw in message for kw in _SEND_KEYWORDS)


def _extract_trigger_type(message: str) -> str | None:
    for keyword, trigger in _TRIGGER_TYPE_MAP.items():
        if keyword in message:
            return trigger
    return None


def _extract_customer_id(message: str) -> str | None:
    m = re.search(r'CUSTOMER_\d+', message)
    return m.group(0) if m else None


def _extract_rule_id(message: str) -> str | None:
    m = re.search(r'RULE_[A-Z0-9_]+', message)
    return m.group(0) if m else None


class NotificationAgent(AbstractAgent):
    """알림 규칙 조회 및 알림 발송을 담당하는 Sub Agent."""

    @property
    def agent_id(self) -> str:
        return "NOTIFICATION_AGENT"

    async def run(self, db: Session, input: AgentInput) -> AgentOutput:
        from app.tools.tool_gateway import invoke_tool
        from app.trace.trace_service import Timer

        wants_send = _wants_send(input.message)

        api_results: list[dict] = []
        for api_id in input.api_ids:
            if api_id == "MOCK_NOTIFICATION_SEND" and not wants_send:
                # 발송 의사 없으면 스킵
                continue

            if api_id == "MOCK_NOTIFICATION_RULES":
                trigger_type = _extract_trigger_type(input.message)
                params: dict = {}
                if trigger_type:
                    params["trigger_type"] = trigger_type

            elif api_id == "MOCK_NOTIFICATION_SEND":
                rule_id     = _extract_rule_id(input.message) or "RULE_RATE_CHANGE"
                customer_id = _extract_customer_id(input.message) or "CUSTOMER_001"
                params = {
                    "rule_id":      rule_id,
                    "customer_id":  customer_id,
                    "trigger_data": {},
                }
            else:
                params = {}

            t = Timer()
            result = await invoke_tool(db, api_id, params=params)
            latency_ms = result.latency_ms if result.latency_ms is not None else t.elapsed_ms()
            api_results.append({
                "api_id":        api_id,
                "status":        result.status,
                "data":          result.data,
                "error":         result.error,
                "latency_ms":    latency_ms,
                "output_masked": result.output_masked,
            })

        success_count = sum(1 for r in api_results if r["status"] == "success")
        confidence = success_count / len(api_results) if api_results else 0.0

        return AgentOutput(
            agent_id=self.agent_id,
            api_results=api_results,
            confidence=confidence,
            metadata={
                "processed_apis": len(api_results),
                "send_requested": wants_send,
            },
        )
