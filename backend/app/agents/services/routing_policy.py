from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agents.agent_registry import get_all_agents, route_by_concepts
from app.agents.concept_constants import (
    AGENT_SERIAL_PREREQUISITE,
    CONCEPT_CATEGORY_HINT,
    CONFIDENCE_DIRECT,
    CONFIDENCE_EXPANDED,
    DECISION_RULES,
    SEARCH_AGENT_TRIGGER_KEYWORDS,
    SLOT_CONCEPT_MAP,
    SLOT_LABEL_KO,
    SLOT_TOOL_MAP,
    classify_concept,
    get_threshold,
)
from app.schemas.decision_trace import (
    AnswerSlot,
    ClassifiedConcepts,
    ConceptCategory,
    ConceptItem,
    RejectedAgentV2,
    SelectedAgentV2,
)


@dataclass
class RoutingDecision:
    route_result: object
    classified: ClassifiedConcepts
    routed_agents: list[str]
    triggered_rules: list[dict]
    selected_agents_v2: list[SelectedAgentV2]
    rejected_agents_v2: list[RejectedAgentV2]
    agent_selection_rows: list[dict]
    concept_trace_rows: list[dict]


class RoutingPolicy:
    def route(
        self,
        db: Session,
        *,
        all_concepts: list[str],
        detected: list[str],
        detected_set: set[str],
        intent_keywords: list[str],
    ) -> RoutingDecision:
        route_result = route_by_concepts(db, all_concepts)
        routed_agents = [item.agent_id for item in route_result.routing]
        classified = self.classify_concepts(detected, all_concepts, detected_set)
        triggered_rules, selected_agents_v2, rejected_agents_v2 = self.evaluate_decision_rules(
            classified=classified,
            routed_agents=routed_agents,
            all_agents=[
                agent.agent_id
                for agent in get_all_agents(db)
                if str(agent.agent_type).lower() != "leader" and agent.agent_id != "LEADER_AGENT"
            ],
            intent_keywords=intent_keywords,
        )

        selected_map = {item.agent_id: item.concept_ids for item in route_result.routing}
        agent_selection_rows: list[dict] = []
        for agent in get_all_agents(db):
            if str(agent.agent_type).lower() == "leader" or agent.agent_id == "LEADER_AGENT":
                continue
            matched_concepts = selected_map.get(agent.agent_id, [])
            is_selected = agent.agent_id in selected_map
            agent_selection_rows.append(
                {
                    "agent_id": agent.agent_id,
                    "selected": is_selected,
                    "score": float(len(matched_concepts)) if is_selected else 0.0,
                    "matched_concepts": matched_concepts,
                    "reason": (
                        f"Matched concepts: {matched_concepts}"
                        if is_selected
                        else "No matched concepts from this request"
                    ),
                    "rejection_reason": (
                        None if is_selected else "No concept-to-agent mapping selected for this request"
                    ),
                }
            )

        selected_v2_map = {agent.agent_name: agent for agent in selected_agents_v2}
        rejected_v2_map = {agent.agent_name: agent for agent in rejected_agents_v2}
        rule_agent_map = {rule["rule_id"]: rule.get("required_agent") for rule in DECISION_RULES}
        agent_rule_ids: dict[str, list[str]] = {}
        for rule in triggered_rules:
            if rule["triggered"]:
                target = rule_agent_map.get(rule["rule_id"])
                if target:
                    agent_rule_ids.setdefault(target, []).append(rule["rule_id"])

        for row in agent_selection_rows:
            agent_id = row["agent_id"]
            if row["selected"] and agent_id in selected_v2_map:
                v2 = selected_v2_map[agent_id]
                row["reason"] = v2.reason
                row["role"] = v2.role
                row["execution_mode"] = v2.execution_mode
                row["tools_assigned"] = v2.tools
                row["decision_rule_ids"] = agent_rule_ids.get(agent_id, [])
            elif not row["selected"] and agent_id in rejected_v2_map:
                row["rejection_reason"] = rejected_v2_map[agent_id].reason
                row["role"] = None
                row["execution_mode"] = None
                row["tools_assigned"] = []
                row["decision_rule_ids"] = []

        concept_trace_rows = [
            {
                "concept_id": concept_id,
                "detection_stage": "direct",
                "confidence": 0.95,
                "source_type": "query",
                "source_terms": [concept_id.replace("CONCEPT_", "").lower()],
                "reason": "Matched from query text or intent keyword",
            }
            for concept_id in detected
        ]
        concept_trace_rows.extend(
            {
                "concept_id": concept_id,
                "detection_stage": "expanded",
                "confidence": 0.7,
                "source_type": "ontology",
                "source_terms": [],
                "reason": "Expanded via business_concept_relation weight >= 0.7",
            }
            for concept_id in all_concepts
            if concept_id not in detected_set
        )
        confidence_map = {item.name: item.confidence for item in classified.all_concepts()}
        for row in concept_trace_rows:
            if row["concept_id"] in confidence_map:
                row["confidence"] = confidence_map[row["concept_id"]]

        return RoutingDecision(
            route_result=route_result,
            classified=classified,
            routed_agents=routed_agents,
            triggered_rules=triggered_rules,
            selected_agents_v2=selected_agents_v2,
            rejected_agents_v2=rejected_agents_v2,
            agent_selection_rows=agent_selection_rows,
            concept_trace_rows=concept_trace_rows,
        )

    def classify_concepts(
        self,
        detected: list[str],
        all_concepts: list[str],
        detected_set: set[str],
    ) -> ClassifiedConcepts:
        core: list[ConceptItem] = []
        supporting: list[ConceptItem] = []
        reference: list[ConceptItem] = []
        category_order = [ConceptCategory.CORE, ConceptCategory.SUPPORTING, ConceptCategory.REFERENCE]

        for concept_id in all_concepts:
            is_direct = concept_id in detected_set
            confidence = CONFIDENCE_DIRECT if is_direct else CONFIDENCE_EXPANDED
            thresholds = get_threshold(concept_id)
            hint = CONCEPT_CATEGORY_HINT.get(concept_id)
            stage = "직접 감지" if is_direct else "관계 확장"
            demoted_from = None
            promoted_from = None

            if hint:
                category = None
                target_categories = category_order[category_order.index(hint):]
                for candidate in target_categories:
                    if confidence >= thresholds[candidate.value]:
                        category = candidate
                        break
                if category is None:
                    continue
                if category != hint:
                    demoted_from = hint
            else:
                category = classify_concept(concept_id, confidence)
                if category is None:
                    continue

            threshold = thresholds[category.value]
            item = ConceptItem(
                name=concept_id,
                category=category,
                confidence=confidence,
                threshold=threshold,
                reason=f"{stage} → confidence {confidence:.2f} / threshold {threshold:.2f}",
                promoted_from=promoted_from,
                demoted_from=demoted_from,
            )
            if category == ConceptCategory.CORE:
                core.append(item)
            elif category == ConceptCategory.SUPPORTING:
                supporting.append(item)
            else:
                reference.append(item)

        return ClassifiedConcepts(core=core, supporting=supporting, reference=reference)

    def evaluate_decision_rules(
        self,
        *,
        classified: ClassifiedConcepts,
        routed_agents: list[str],
        all_agents: list[str],
        intent_keywords: list[str],
    ) -> tuple[list[dict], list[SelectedAgentV2], list[RejectedAgentV2]]:
        triggered_rules: list[dict] = []
        selected_map: dict[str, SelectedAgentV2] = {}

        core_names = {item.name for item in classified.core}
        supporting_names = {item.name for item in classified.supporting}
        reference_names = {item.name for item in classified.reference}

        for rule in DECISION_RULES:
            trigger_concept = rule.get("trigger_concept")
            trigger_category = rule.get("trigger_category")
            required_agent = rule.get("required_agent")

            if trigger_concept is None:
                triggered_rules.append(
                    {"rule_id": rule["rule_id"], "rule_name": rule["rule_name"], "triggered": True}
                )
                continue

            triggered = False
            if trigger_category == ConceptCategory.CORE and trigger_concept in core_names:
                triggered = True
            elif trigger_category == ConceptCategory.SUPPORTING and trigger_concept in supporting_names:
                triggered = True
            elif trigger_category == ConceptCategory.REFERENCE and trigger_concept in reference_names:
                triggered = True

            triggered_rules.append(
                {"rule_id": rule["rule_id"], "rule_name": rule["rule_name"], "triggered": triggered}
            )
            if not triggered or not required_agent:
                continue

            all_items = classified.all_concepts()
            concept_item = next((item for item in all_items if item.name == trigger_concept), None)
            score = concept_item.confidence if concept_item else 0.7

            if required_agent not in selected_map:
                selected_map[required_agent] = SelectedAgentV2(
                    agent_name=required_agent,
                    role=rule.get("role") or "general",
                    score=score,
                    reason=f"{rule['rule_name']} 트리거됨",
                    execution_mode=rule.get("execution_mode") or "normal",
                    tools=list(rule.get("tools") or []),
                    depends_on=[] if required_agent in AGENT_SERIAL_PREREQUISITE else AGENT_SERIAL_PREREQUISITE,
                )
            elif score > selected_map[required_agent].score:
                selected_map[required_agent] = SelectedAgentV2(
                    **{**selected_map[required_agent].model_dump(), "score": score}
                )

        selected_agents = list(selected_map.values())
        selected_names = {agent.agent_name for agent in selected_agents}
        query_str = " ".join(intent_keywords)
        if any(keyword in query_str for keyword in SEARCH_AGENT_TRIGGER_KEYWORDS):
            if "SEARCH_AGENT" not in selected_names:
                selected_agents.append(
                    SelectedAgentV2(
                        agent_name="SEARCH_AGENT",
                        role="history_search",
                        score=0.75,
                        reason="상담이력 조회 또는 비정형 검색 키워드 감지",
                        execution_mode="normal",
                        tools=["MOCK_COUNSELING_HISTORY", "MOCK_DOCUMENT_SEARCH"],
                        depends_on=[],
                    )
                )
                selected_names.add("SEARCH_AGENT")

        rejected_agents: list[RejectedAgentV2] = []
        for agent_name in all_agents:
            if agent_name in selected_names:
                continue
            if agent_name == "SEARCH_AGENT":
                reason = "DOCUMENT_SEARCH는 POLICY_AGENT 대체 Tool로 처리 가능하며 상담이력 검색 키워드가 감지되지 않음."
                score = 0.41
            else:
                reason = f"{agent_name}에 해당하는 Concept가 Core/Supporting으로 분류되지 않음"
                score = 0.20
            rejected_agents.append(RejectedAgentV2(agent_name=agent_name, score=score, reason=reason))

        return triggered_rules, selected_agents, rejected_agents

    def extract_answer_slots(self, classified: ClassifiedConcepts) -> list[AnswerSlot]:
        concept_to_slot: dict[str, str] = {}
        for slot_name, concept_ids in SLOT_CONCEPT_MAP.items():
            for concept_id in concept_ids:
                if concept_id not in concept_to_slot:
                    concept_to_slot[concept_id] = slot_name

        slots: list[AnswerSlot] = []
        seen_slots: set[str] = set()
        for item in classified.core + classified.supporting:
            slot_name = concept_to_slot.get(item.name)
            if slot_name is None or slot_name in seen_slots:
                continue
            seen_slots.add(slot_name)
            slots.append(
                AnswerSlot(
                    slot_name=slot_name,
                    label_ko=SLOT_LABEL_KO.get(slot_name, slot_name),
                    concept_ids=SLOT_CONCEPT_MAP.get(slot_name, [item.name]),
                    tools=SLOT_TOOL_MAP.get(slot_name, []),
                )
            )
        return slots

