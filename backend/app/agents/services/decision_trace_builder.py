from __future__ import annotations

from app.agents.concept_constants import AGENT_PARALLEL_GROUPS, AGENT_SERIAL_PREREQUISITE
from app.schemas.decision_trace import (
    AnswerSlot,
    AnswerSlotRanking,
    ClassifiedConcepts,
    ContextLoaded,
    DecisionRule,
    IntentV2,
    LeaderDecisionV2,
    RejectedAgentV2,
    SelectedAgentV2,
)


class DecisionTraceBuilder:
    def __init__(self, *, llm_enabled: bool) -> None:
        self._llm_enabled = llm_enabled

    def build_decision_v2(
        self,
        *,
        request_id: str,
        session_id: str | None,
        user_query: str,
        memory_turns: int,
        ltm_turns: int,
        intent_data: dict,
        intent_confidence: float,
        classified: ClassifiedConcepts,
        triggered_rules: list[dict],
        selected_agents_v2: list[SelectedAgentV2],
        rejected_agents_v2: list[RejectedAgentV2],
        answer_slots: list[AnswerSlot] | None = None,
        slot_rankings: list[AnswerSlotRanking] | None = None,
        risk_flags: list[str] | None = None,
        actions_taken: list[str] | None = None,
        requires_disclaimer: bool = False,
    ) -> LeaderDecisionV2:
        rules = [
            DecisionRule(
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                triggered=rule["triggered"],
            )
            for rule in triggered_rules
        ]

        core_names = [item.name for item in classified.core]
        supporting_names = [item.name for item in classified.supporting]

        return LeaderDecisionV2(
            request_id=request_id,
            session_id=session_id,
            user_query=user_query,
            context_loaded=ContextLoaded(
                short_memory_turns=memory_turns,
                long_term_summary=f"{ltm_turns}턴 장기 이력 로드" if ltm_turns else None,
                context_applied=memory_turns > 0 or ltm_turns > 0,
            ),
            intent=IntentV2(
                name=intent_data.get("intent", "INQUIRY"),
                confidence=intent_confidence,
                reason=f"키워드 기반 의도 분류: {intent_data.get('keywords', [])}",
                fallback_triggered=not self._llm_enabled,
                fallback_reason=(
                    "OPENAI_API_KEY 미설정으로 템플릿 모드 동작"
                    if not self._llm_enabled
                    else None
                ),
            ),
            concepts=classified,
            decision_rules_applied=rules,
            selected_agents=selected_agents_v2,
            rejected_agents=rejected_agents_v2,
            execution_strategy="parallel",
            parallelization_groups=AGENT_PARALLEL_GROUPS,
            serial_prerequisite=AGENT_SERIAL_PREREQUISITE,
            decision_reason=(
                f"Concept 분류 기반 결정 룰 적용. "
                f"Core: {core_names}, Supporting: {supporting_names}. "
                f"선택 Agent: {[agent.agent_name for agent in selected_agents_v2]}."
            ),
            answer_slots=answer_slots or [],
            slot_rankings=slot_rankings or [],
            risk_flags=risk_flags or [],
            actions_taken=actions_taken or [],
            requires_disclaimer=requires_disclaimer,
        )
