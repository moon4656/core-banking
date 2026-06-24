# leader.py — Leader Agent: 요청 분석 → Sub-Agent 조율 → 결과 통합
#
# [전체 처리 흐름]
#
#   LeaderAgent.run(message, session_id)
#       │
#       ├─ 1. Short Memory 로드 (Redis)
#       │       └─ 이전 대화 이력을 불러와 컨텍스트로 활용
#       │
#       ├─ 2. 의도 분석 (LLM)
#       │       └─ 질문 유형(조회/비교/추천/신청)과 핵심 키워드 추출
#       │
#       ├─ 3. Concept 탐지 + 온톨로지 관계 확장
#       │       └─ 키워드 → concept 검색 → 관련 concept 자동 추가
#       │          예: 신용대출 → 금리, 필요서류, 정책도 자동 포함
#       │
#       ├─ 4. Sub-Agent 라우팅 (DB 매핑)
#       │       └─ concept → agent_concept_mapping → 담당 Agent 결정
#       │
#       ├─ 5. Tool 실행 (Tool Hub)
#       │       └─ 각 concept에 매핑된 API 순서대로 호출
#       │
#       ├─ 6. 결과 Re-ranking

#       │       └─ 데이터 충실도 + 의도 관련성으로 결과 점수 계산 및 정렬
#       │
#       ├─ 7. LLM 최종 요약 (GPT-4o)
#       │       └─ 의도 + 이전 대화 + 재정렬된 결과로 최종 한국어 답변 생성
#       │
#       └─ 8. Short Memory 저장 (Redis)
#               └─ 이번 턴(질문+답변)을 저장해 다음 요청에서 활용

import json
import re

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.agents.memory import load_history, save_turn
from app.agents.long_term_memory import load_long_term_history, save_long_term_memory
from app.agents.agent_registry import get_all_agents, route_by_concepts
from app.agents.base_agent import AgentInput
from app.agents.services.answer_composer import AnswerComposer
from app.agents.services.clarification_service_adapter import ClarificationServiceAdapter
from app.agents.services.concept_resolution_service import ConceptResolutionService
from app.agents.services.execution_planner import ExecutionPlanner
from app.agents.services.routing_policy import RoutingPolicy
from app.agents.graph_builder import build_decision_graph
from app.agents.forex_agent import ForexAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.product_agent import ProductAgent
from app.agents.rate_agent import RateAgent
from app.agents.search_agent import SearchAgent
from app.core.config import settings
from app.knowledge.concept_service import (
    detect_concepts_in_message,
    get_apis_by_concept,
    search_concepts,
)
from app.models.knowledge_model import BusinessConceptRelation
from app.models.trace_model import LeaderDecision
from app.agents.concept_constants import (
    AGENT_PARALLEL_GROUPS,
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
from app.schemas.ai_gateway import (
    ExecutionPlan,
    ExecutionStep,
    LeaderResult,
    StepResult,
)
from app.schemas.decision_trace import (
    AnswerSlot,
    AnswerSlotRanking,
    ClassifiedConcepts,
    ConceptCategory,
    ConceptItem,
    ContextLoaded,
    DecisionRule,
    IntentV2,
    LeaderDecisionV2,
    RejectedAgentV2,
    SelectedAgentV2,
)
from app.services.decision_trace_service import (
    save_agent_selection_rows,
    save_concept_detections,
    save_decision_trace_core,
    save_final_answer_trace,
    save_reranking_trace,
    save_tool_execution_rows,
)
from app.services.monitoring_service import _check_grounding
from app.trace.evidence_scorer import rank_evidence_by_slots
from app.trace.evidence_service import link_related_evidence, save_evidence_with_score
from app.trace.trace_service import Timer, record_event

# agent_id → Sub Agent 클래스 매핑 (새 Agent 추가 시 여기에 등록)
_AGENT_REGISTRY: dict[str, type] = {
    "PRODUCT_AGENT":       ProductAgent,
    "RATE_AGENT":          RateAgent,
    "POLICY_AGENT":        PolicyAgent,
    "SEARCH_AGENT":        SearchAgent,
    "FOREX_AGENT":         ForexAgent,
    "NOTIFICATION_AGENT":  NotificationAgent,
}


# ─────────────────────────────────────────────────────────────
# 의도(Intent) 유형 상수
# ─────────────────────────────────────────────────────────────
INTENT_INQUIRY = "INQUIRY"
INTENT_COMPARISON = "COMPARISON"
INTENT_RECOMMENDATION = "RECOMMENDATION"
INTENT_APPLICATION = "APPLICATION"
INTENT_OTHER = "OTHER"

_API_INTENT_RELEVANCE = {
    "MOCK_PRODUCT_LOOKUP": ["product", "loan", "??", "??", "recommendation"],
    "MOCK_RATE_LOOKUP": ["rate", "??", "??", "inquiry", "comparison"],
    "MOCK_POLICY_LOOKUP": ["policy", "??", "??", "application"],
    "MOCK_DOCUMENT_SEARCH": ["document", "??", "??", "application"],
    "MOCK_RATE_SIMULATION": ["simulation", "?????", "??", "??", "comparison"],
    "MOCK_ELIGIBILITY_CHECK": ["eligibility", "??", "??", "??", "application"],
    "MOCK_COUNSELING_HISTORY": ["history", "??", "??", "inquiry"],
    "MOCK_BRANCH_LOOKUP": ["branch", "??", "???", "??", "inquiry"],
}

_FOCUS_KEYWORDS_CACHE: dict[str, list[str]] | None = None
_API_CONCEPT_CACHE: dict[str, list[str]] | None = None


def _load_focus_keywords(db) -> dict[str, list[str]]:
    global _FOCUS_KEYWORDS_CACHE
    if _FOCUS_KEYWORDS_CACHE is not None:
        return _FOCUS_KEYWORDS_CACHE

    from app.models.knowledge_model import IntentTermSynonym

    rows = db.query(IntentTermSynonym.intent, IntentTermSynonym.term).filter(
        IntentTermSynonym.intent.like("MOCK_%"),
        IntentTermSynonym.is_active == True,
    ).all()

    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.intent, []).append(row.term)

    _FOCUS_KEYWORDS_CACHE = result
    return result


def _load_api_concept_map(db) -> dict[str, list[str]]:
    global _API_CONCEPT_CACHE
    if _API_CONCEPT_CACHE is not None:
        return _API_CONCEPT_CACHE

    from app.models.knowledge_model import ConceptApiMapping

    rows = db.query(ConceptApiMapping.api_id, ConceptApiMapping.concept_id).all()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.api_id, []).append(row.concept_id)

    _API_CONCEPT_CACHE = result
    return result


def clear_focus_keywords_cache() -> None:
    global _FOCUS_KEYWORDS_CACHE, _API_CONCEPT_CACHE
    _FOCUS_KEYWORDS_CACHE = None
    _API_CONCEPT_CACHE = None


def _detect_concepts_via_synonyms(message: str, db) -> list[str]:
    focus_keywords = _load_focus_keywords(db)
    api_concept_map = _load_api_concept_map(db)
    msg_lower = message.lower()

    fallback_concepts: list[str] = []
    seen: set[str] = set()
    for api_id, keywords in focus_keywords.items():
        if any(keyword in msg_lower for keyword in keywords):
            for concept_id in api_concept_map.get(api_id, []):
                if concept_id not in seen:
                    fallback_concepts.append(concept_id)
                    seen.add(concept_id)

    return fallback_concepts


def _filter_results_by_question(message: str, results: list[StepResult], db=None) -> list[StepResult]:
    focus_keywords = _load_focus_keywords(db) if db is not None else {}
    msg_lower = message.lower()

    matched_apis: set[str] = set()
    for api_id, keywords in focus_keywords.items():
        if any(keyword in msg_lower for keyword in keywords):
            matched_apis.add(api_id)

    if not matched_apis:
        return results

    if "MOCK_RATE_SIMULATION" in matched_apis:
        matched_apis.discard("MOCK_RATE_LOOKUP")
        matched_apis.discard("MOCK_PRODUCT_LOOKUP")

    if "MOCK_PERSONALIZED_RATE_LOOKUP" in matched_apis:
        matched_apis.discard("MOCK_RATE_LOOKUP")
        matched_apis.discard("MOCK_PRODUCT_LOOKUP")

    if "MOCK_CURRENCY_EXCHANGE_CALC" in matched_apis:
        matched_apis.discard("MOCK_EXCHANGE_RATE_LOOKUP")
        matched_apis.discard("MOCK_FOREIGN_DEPOSIT_RATE")

    if "MOCK_FOREIGN_REMITTANCE" in matched_apis:
        matched_apis.discard("MOCK_FOREIGN_DEPOSIT_RATE")

    if "MOCK_FOREIGN_DEPOSIT_RATE" in matched_apis:
        matched_apis.discard("MOCK_RATE_LOOKUP")
        matched_apis.discard("MOCK_RATE_SIMULATION")
        matched_apis.discard("MOCK_PERSONALIZED_RATE_LOOKUP")

    if "MOCK_NOTIFICATION_RULES" in matched_apis or "MOCK_NOTIFICATION_SEND" in matched_apis:
        matched_apis.discard("MOCK_RATE_LOOKUP")
        matched_apis.discard("MOCK_RATE_SIMULATION")
        matched_apis.discard("MOCK_PERSONALIZED_RATE_LOOKUP")
        matched_apis.discard("MOCK_PRODUCT_LOOKUP")
        matched_apis.discard("MOCK_POLICY_LOOKUP")
        matched_apis.discard("MOCK_FOREIGN_DEPOSIT_RATE")
        matched_apis.discard("MOCK_EXCHANGE_RATE_LOOKUP")

    focused = [result for result in results if result.api_id in matched_apis]
    return focused if focused else results

class LeaderAgent:
    def __init__(self):
        self._llm_enabled = bool(settings.OPENAI_API_KEY)
        self._concept_resolution_service = ConceptResolutionService()
        self._routing_policy = RoutingPolicy()
        self._execution_planner = ExecutionPlanner()
        self._clarification_adapter = ClarificationServiceAdapter()
        self._answer_composer = AnswerComposer(summarize=self._summarize, extract_answer_slots=self._routing_policy.extract_answer_slots)

    async def run(self, db: Session, request_id: str, message: str, session_id: str | None, owner_name: str | None = None, owner_role: str | None = None) -> "LeaderResult":
        run_timer = Timer()
        history = load_history(session_id)
        memory_turns = len(history) // 2
        record_event(db, request_id=request_id, event_type="MEMORY_LOADED", input_data={"session_id": session_id}, output_data={"turns_loaded": memory_turns})
        ltm_history = load_long_term_history(db, session_id, user_id=owner_name)
        record_event(db, request_id=request_id, event_type="LTM_LOADED", input_data={"session_id": session_id}, output_data={"ltm_turns_loaded": len(ltm_history)})

        pending = self._clarification_adapter.load_pending(session_id)
        if pending and pending.get("turns", 0) < 3:
            snapshot = pending
            pending, question = self._clarification_adapter.try_resolve(session_id=session_id, pending=pending, message=message)
            if question:
                memory_save = save_turn(session_id, message, question)
                if session_id:
                    record_event(db, request_id=request_id, event_type="MEMORY_SAVED", input_data={"session_id": session_id}, output_data=memory_save)
                return LeaderResult(plan=ExecutionPlan(request_id=request_id, message=message, detected_concepts=snapshot.get("detected_concepts", []), routed_agents=[], steps=[]), raw_results=[], ranked_results=[], intent=snapshot.get("intent_data", {}), memory_turns=memory_turns, answer=question, needs_clarification=True, clarification_question=question)
            if pending is None:
                message = snapshot.get("original_message", message) + " " + message

        intent_data = await self._analyze_intent(message, history, ltm_history)
        record_event(db, request_id=request_id, event_type="INTENT_ANALYZED", input_data={"message": message}, output_data=intent_data)
        resolved = self._concept_resolution_service.resolve(db=db, message=message, intent_keywords=intent_data.get("keywords", []))
        detected, all_concepts, detected_set = resolved.detected, resolved.all_concepts, resolved.detected_set
        expanded_concepts = [concept_id for concept_id in all_concepts if concept_id not in detected_set]
        record_event(db, request_id=request_id, event_type="CONCEPT_DETECTED", input_data={"message": message}, output_data={"detected_concepts": detected, "expanded_concepts": expanded_concepts, "total_concepts": all_concepts})

        routing = self._routing_policy.route(db=db, all_concepts=all_concepts, detected=detected, detected_set=detected_set, intent_keywords=intent_data.get("keywords", []))
        route_result = routing.route_result
        routed_agents = routing.routed_agents
        classified_concepts = routing.classified
        answer_slots = self._routing_policy.extract_answer_slots(classified_concepts)
        record_event(db, request_id=request_id, event_type="AGENT_SELECTED", input_data={"concept_ids": all_concepts}, output_data={"routed_agents": routed_agents, "unrouted_concepts": route_result.unrouted_concept_ids})

        if session_id and not pending:
            missing_slots = self._clarification_adapter.check_missing_slots(message, list(detected_set), intent_data.get("intent", INTENT_INQUIRY))
            if missing_slots:
                question = self._clarification_adapter.build_question(missing_slots[0])
                self._clarification_adapter.save_pending(session_id, {"original_message": message, "intent_data": intent_data, "detected_concepts": list(detected_set), "missing_slots": missing_slots, "filled_slots": {}, "turns": 1})
                memory_save = save_turn(session_id, message, question)
                record_event(db, request_id=request_id, event_type="MEMORY_SAVED", input_data={"session_id": session_id}, output_data=memory_save)
                return LeaderResult(plan=ExecutionPlan(request_id=request_id, message=message, detected_concepts=list(detected_set), routed_agents=[], steps=[]), raw_results=[], ranked_results=[], intent=intent_data, memory_turns=memory_turns, answer=question, needs_clarification=True, clarification_question=question)

        steps, seen_apis = self._execution_planner.build_steps(db, route_result)
        raw_results = []
        evidence_results = []
        tool_execution_rows: list[dict] = []
        evidence_map: dict[str, list[int]] = {}
        agent_api_results: dict[str, list[dict]] = {}
        agent_latencies: dict[str, int] = {}

        for route_item in route_result.routing:
            agent_cls = _AGENT_REGISTRY.get(route_item.agent_id)
            if not agent_cls:
                continue
            api_ids = [step.api_id for step in steps if step.agent_id == route_item.agent_id]
            if not api_ids:
                continue
            agent_output = await agent_cls().run(db, AgentInput(message=message, intent=intent_data, concept_ids=route_item.concept_ids, api_ids=api_ids, session_id=session_id or "", request_id=request_id))
            agent_api_results[route_item.agent_id] = list(agent_output.api_results)
            agent_latencies[route_item.agent_id] = sum((api_res.get("latency_ms") or 0) for api_res in agent_output.api_results)
            for api_res in agent_output.api_results:
                raw_results.append(StepResult(api_id=api_res["api_id"], status=api_res["status"], data=api_res.get("data"), error=api_res.get("error")))
                record_event(db, request_id=request_id, event_type="TOOL_INVOKED", agent_id=route_item.agent_id, tool_id=api_res["api_id"], input_data={"api_id": api_res["api_id"]}, output_data={"status": api_res["status"]})
                if api_res["status"] == "success" and api_res.get("data"):
                    evidence = save_evidence_with_score(
                        db=db,
                        request_id=request_id,
                        concept_id=route_item.concept_ids[0] if route_item.concept_ids else None,
                        source_id=api_res["api_id"],
                        content=api_res.get("data"),
                        intent=intent_data.get("intent", INTENT_INQUIRY),
                        response_latency_ms=api_res.get("latency_ms") or 0,
                        agent_id=route_item.agent_id,
                    )
                    evidence_map.setdefault(api_res["api_id"], []).append(evidence.id)
                    evidence_results.append({
                        "api_id": api_res["api_id"],
                        "evidence_id": evidence.id,
                        "confidence_score": evidence.confidence_score,
                    })
                tool_execution_rows.append(
                    {
                        "agent_id": route_item.agent_id,
                        "tool_code": api_res["api_id"],
                        "concept_ids": route_item.concept_ids,
                        "input_summary": f"message={message[:80]}",
                        "output_summary": self._summarize_tool_output(api_res.get("data")),
                        "status": api_res["status"],
                        "latency_ms": api_res.get("latency_ms"),
                        "error_summary": api_res.get("error"),
                        "evidence_ids": evidence_map.get(api_res["api_id"], []),
                    }
                )

        link_related_evidence(db, request_id)

        plan = self._execution_planner.build_plan(request_id=request_id, message=message, detected_concepts=all_concepts, routed_agents=routed_agents, steps=steps)
        record_event(db, request_id=request_id, event_type="PLAN_CREATED", output_data={"step_count": len(steps), "api_ids": list(seen_apis)})
        ranked_results = self._rerank(raw_results, intent_data)
        answer, ranked_results, answer_slots, slot_rankings = await self._answer_composer.compose(db=db, request_id=request_id, message=message, intent_data=intent_data, classified=classified_concepts, raw_results=ranked_results, history=history, ltm_history=ltm_history)

        from app.agents.validator import ValidationChecker
        validation = ValidationChecker().run_all(answer=answer, evidence_results=evidence_results, intent=intent_data.get("intent", INTENT_INQUIRY), user_role=owner_role or "READONLY")
        if validation.sanitized_answer is not None:
            answer = validation.sanitized_answer

        memory_save = save_turn(session_id, message, answer)
        if session_id:
            record_event(db, request_id=request_id, event_type="MEMORY_SAVED", input_data={"session_id": session_id}, output_data=memory_save)

        ltm_save = {
            "saved": False,
            "reason": "missing_session_id" if not session_id else "not_attempted",
            "turn_index": None,
            "question_summary": "",
            "answer_summary": "",
        }
        try:
            ltm_save = save_long_term_memory(db=db, session_id=session_id, intent=intent_data.get("intent", INTENT_INQUIRY), detected_concepts=all_concepts, keywords=intent_data.get("keywords", []), question=message, answer=answer, user_id=owner_name, question_summary=message[:300], answer_summary=answer[:500])
        except Exception:
            pass
        if session_id:
            record_event(db, request_id=request_id, event_type="LTM_SAVED", input_data={"session_id": session_id, "user_id": owner_name}, output_data=ltm_save)

        request_meta = {
            "channel": "chat",
            "owner_name": owner_name,
            "owner_role": owner_role,
            "session_id": session_id,
        }
        memory_summary = {
            "short_memory": {
                "loaded": bool(history),
                "summary": f"{memory_turns} turns loaded" if history else None,
                "items_count": len(history),
                "impact": ["Used recent conversation context"] if history else [],
                "items": history,
            },
            "long_term_memory": {
                "loaded": bool(ltm_history),
                "summary": f"{len(ltm_history)} long-term entries loaded" if ltm_history else None,
                "items_count": len(ltm_history),
                "impact": ["Used historical counseling summaries"] if ltm_history else [],
                "items": ltm_history,
            },
        }
        intent_confidence = (sum(1 for r in raw_results if r.status == "success") / len(raw_results) if raw_results else 0.0)
        latency_summary = {
            "total_ms": run_timer.elapsed_ms(),
            "tool_count": len(tool_execution_rows),
            "memory_turns": memory_turns,
            "ltm_turns": len(ltm_history),
        }

        save_decision_trace_core(
            db,
            request_id=request_id,
            session_id=session_id,
            owner_name=owner_name,
            owner_role=owner_role,
            user_query=message,
            normalized_query=" ".join(message.split()),
            request_meta=request_meta,
            memory_summary=memory_summary,
            intent_analysis={
                "intent": intent_data.get("intent"),
                "confidence": intent_confidence,
                "keywords": intent_data.get("keywords", []),
                "urgency": intent_data.get("urgency"),
                "reason": f"Derived from message and context keywords: {intent_data.get('keywords', [])}",
            },
            latency=latency_summary,
            status="completed",
        )
        save_concept_detections(db, request_id, routing.concept_trace_rows)
        save_agent_selection_rows(db, request_id, routing.agent_selection_rows)
        save_tool_execution_rows(db, request_id, tool_execution_rows)
        save_reranking_trace(
            db,
            request_id=request_id,
            criteria_weights={"focus_match": 0.5, "success": 0.3, "intent_relevance": 0.2},
            candidates=[
                {"api_id": result.api_id, "status": result.status, "has_data": bool(result.data)}
                for result in ranked_results
            ],
            selected_evidence_ids=[item["evidence_id"] for item in evidence_results],
            reason="Ranked results filtered toward question focus and successful grounded outputs",
        )
        save_final_answer_trace(
            db,
            request_id=request_id,
            answer=answer,
            answer_summary=answer[:500],
            used_evidence_ids=[item["evidence_id"] for item in evidence_results],
            grounding_summary=f"Grounded by {len(evidence_results)} evidence items across {len(tool_execution_rows)} tool executions",
        )

        db.add(
            LeaderDecision(
                request_id=request_id,
                detected_intent=intent_data.get("intent"),
                detected_concepts=all_concepts,
                direct_concepts=detected,
                expanded_concepts=expanded_concepts,
                selected_agents=routed_agents,
                reasoning={
                    "leader_reason": "Concept-to-agent routing completed",
                    "unrouted_concepts": route_result.unrouted_concept_ids,
                },
                confidence_score=intent_confidence,
                total_steps=len(steps),
                memory_turns=memory_turns,
                ltm_turns=len(ltm_history),
                answer=answer,
            )
        )
        db.commit()
        build_decision_graph(
            db,
            request_id=request_id,
            message=message,
            session_id=session_id,
            memory_turns=memory_turns,
            ltm_turns=len(ltm_history),
            intent_data=intent_data,
            intent_ms=0,
            detected=detected,
            all_concepts=all_concepts,
            detected_set=detected_set,
            route_result=route_result,
            routed_agents=routed_agents,
            agent_api_results=agent_api_results,
            agent_latencies=agent_latencies,
            ranked_results=ranked_results,
            answer=answer,
            confidence=intent_confidence,
            llm_enabled=self._llm_enabled,
            short_memory_save=memory_save,
            long_term_memory_save=ltm_save,
        )
        record_event(db, request_id=request_id, event_type="RESPONSE_COMPLETED", output_data={"selected_agents": routed_agents, "answer_length": len(answer)})

        decision_v2 = self._build_decision_v2(request_id=request_id, session_id=session_id, user_query=message, memory_turns=memory_turns, ltm_turns=len(ltm_history), intent_data=intent_data, intent_confidence=intent_confidence, classified=classified_concepts, triggered_rules=routing.triggered_rules, selected_agents_v2=routing.selected_agents_v2, rejected_agents_v2=routing.rejected_agents_v2, answer_slots=answer_slots, slot_rankings=rank_evidence_by_slots(answer_slots, evidence_results), risk_flags=validation.risk_flags, actions_taken=validation.actions_taken, requires_disclaimer=validation.requires_disclaimer)
        return LeaderResult(plan=plan, raw_results=raw_results, ranked_results=ranked_results, intent=intent_data, memory_turns=memory_turns, answer=answer, decision_v2=decision_v2, needs_clarification=False, clarification_question=None)

    def _summarize_tool_output(self, data: dict | list | None) -> str | None:
        if data is None:
            return None
        if isinstance(data, list):
            return f"list[{len(data)}]"
        if isinstance(data, dict):
            keys = list(data.keys())[:5]
            return f"dict keys={keys}"
        return str(data)[:200]

    async def _summarize_for_long_term(
        self,
        message: str,
        answer: str,
        intent: str,
        keywords: list[str],
    ) -> tuple[str, str]:
        normalized_question = " ".join(message.split())
        normalized_answer = " ".join(answer.split())

        if not self._llm_enabled:
            return normalized_question[:300], normalized_answer[:500]

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize the counseling turn for long-term memory storage. "
                            "Return JSON only with keys question_summary and answer_summary. "
                            "Each summary must be concise, factual, and under 300 / 500 characters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "intent": intent,
                                "keywords": keywords,
                                "question": message,
                                "answer": answer,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            question_summary = " ".join(str(payload.get("question_summary", "")).split())
            answer_summary = " ".join(str(payload.get("answer_summary", "")).split())
            return (question_summary or normalized_question)[:300], (answer_summary or normalized_answer)[:500]
        except Exception:
            return normalized_question[:300], normalized_answer[:500]

    async def _analyze_intent(
        self,
        message: str,
        history: list[dict],
        ltm_history: list[dict] | None = None,
    ) -> dict:
        """
        LLM으로 사용자 의도를 분석한다.

        [반환 형식]
        {
          "intent": "INQUIRY",
          "keywords": ["신용대출", "금리"],
          "urgency": "medium"
        }

        LTM 이력이 있으면 system 프롬프트에 과거 관심 패턴을 포함해 분류 정확도를 높인다.
        LLM을 사용할 수 없으면 기본값(INQUIRY)을 반환한다.
        """
        if not self._llm_enabled:
            return self._keyword_intent(message)

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # 최근 2턴만 컨텍스트로 사용 (토큰 절약)
        recent_history = history[-4:] if len(history) >= 4 else history

        # LTM에서 과거 관심 키워드 요약 (최대 3턴)
        ltm_hint = ""
        if ltm_history:
            past = ltm_history[-3:]
            patterns = ", ".join(
                f"{h['intent']}({', '.join(h['keywords'][:2])})"
                for h in past if h.get("keywords")
            )
            if patterns:
                ltm_hint = f"\n[고객 과거 상담 패턴: {patterns}]"

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "은행 AI 상담 시스템입니다. 사용자 메시지를 분석해 아래 JSON 형식으로만 응답하세요.\n"
                            "{\n"
                            '  "intent": "INQUIRY|COMPARISON|RECOMMENDATION|APPLICATION|OTHER",\n'
                            '  "keywords": ["핵심 금융 키워드 목록"],\n'
                            '  "urgency": "low|medium|high"\n'
                            "}\n\n"
                            "intent 분류 규칙 (순서대로 적용, 해당하면 즉시 선택):\n"
                            "1. COMPARISON: 메시지에 '비교', '차이', '어느 게', '둘 중', 'vs', '어느쪽'이 포함되면 반드시 COMPARISON\n"
                            "   예) '금리를 비교해줘', 'A은행과 B은행 차이가 뭐야?', '두 상품 중 뭐가 나아?'\n"
                            "2. RECOMMENDATION: 메시지에 '추천', '추천해', '나한테 맞는', '맞춰줘', '어떤 게 좋을까'가 포함되면 반드시 RECOMMENDATION\n"
                            "   예) '나한테 맞는 대출 추천해줘', '어떤 상품이 좋을까요?'\n"
                            "3. APPLICATION: 메시지에 '신청', '가입', '어떻게 해야', '절차', '방법', '신청하려면', '가능한가요', '자격 조건'이 포함되면 반드시 APPLICATION\n"
                            "   예) '신용대출 신청하려면 어떻게 해야 하나요?', '대출 신청 자격 조건이 어떻게 되나요?'\n"
                            "4. INQUIRY: 위 1~3에 해당하지 않는 단순 정보 조회\n"
                            "   예) '금리가 얼마야?', '우대금리 조건이 어떻게 돼요?', '필요한 서류가 뭐예요?'\n"
                            f"5. OTHER: 금융/대출과 전혀 관련 없는 질문{ltm_hint}"
                        ),
                    },
                    *recent_history,
                    {"role": "user", "content": message},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  # 의도 분류는 결정적이어야 함
                max_tokens=200,
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return self._keyword_intent(message)

    def _keyword_intent(self, message: str) -> dict:
        """키워드 기반 의도 분류 — LLM 미사용 또는 LLM 실패 시 fallback."""
        text = message.lower()
        _comparison_kw     = ["비교", "차이", "vs", "어느게", "어느 게", "둘 중", "어느쪽"]
        _recommendation_kw = ["추천", "나한테 맞", "제게 맞", "뭐가 좋", "어떤 게 좋"]
        _application_kw    = ["신청하려면", "어떻게 신청", "가입방법", "신청 방법", "신청 절차",
                              "신청하고 싶", "신청가능", "자격 조건", "신청 자격"]
        if any(kw in text for kw in _comparison_kw):
            intent = INTENT_COMPARISON
        elif any(kw in text for kw in _recommendation_kw):
            intent = INTENT_RECOMMENDATION
        elif any(kw in text for kw in _application_kw):
            intent = INTENT_APPLICATION
        else:
            intent = INTENT_INQUIRY
        return {"intent": intent, "keywords": message.split(), "urgency": "low"}

    def _expand_via_relations(self, db: Session, concept_ids: list[str]) -> list[str]:
        """
        온톨로지 관계(business_concept_relation)를 따라 관련 concept을 확장한다.

        [확장 예시]
        CONCEPT_PERSONAL_CREDIT_LOAN 탐지 →
            관계: includes CONCEPT_INTEREST_RATE (weight=1.0)
                  includes CONCEPT_PREFERENTIAL_RATE (weight=0.8)
                  requires CONCEPT_REQUIRED_DOCUMENT (weight=0.9)
        → 금리, 우대금리, 필요서류 concept도 자동으로 추가됨

        [가중치 임계값]
        weight >= 0.7인 관계만 확장에 포함. 약한 관계는 무시.
        """
        expanded = list(concept_ids)
        seen = set(concept_ids)

        for cid in concept_ids:
            relations = (
                db.query(BusinessConceptRelation)
                .filter(
                    BusinessConceptRelation.source_concept_id == cid,
                    BusinessConceptRelation.weight >= 0.7,  # 강한 관계만 확장
                )
                .all()
            )
            for rel in relations:
                if rel.target_concept_id not in seen:
                    expanded.append(rel.target_concept_id)
                    seen.add(rel.target_concept_id)

        return expanded

    def _rerank(self, results: list[StepResult], intent_data: dict) -> list[StepResult]:
        """
        Sub-Agent 결과를 관련도 점수 순으로 재정렬한다.

        [점수 계산 방식]
        - 기본 점수: 성공 여부 (성공=1.0, 실패=0.0)
        - 데이터 충실도: 반환된 항목 수 × 0.1 (최대 +0.5)
        - 의도 관련도: api_id가 현재 intent와 관련 있으면 +0.5

        [목적]
        LLM에게 가장 관련성 높은 데이터를 먼저 전달 → 답변 품질 향상
        """
        intent = intent_data.get("intent", INTENT_INQUIRY).lower()

        def score(result: StepResult) -> float:
            if result.status != "success" or not result.data:
                return 0.0

            s = 1.0

            # 데이터 충실도 점수
            if isinstance(result.data, dict):
                for list_key in ["products", "rates", "policies", "documents"]:
                    items = result.data.get(list_key, [])
                    if items:
                        s += min(len(items) * 0.1, 0.5)
                        break

            # 의도 관련도 점수
            relevant_intents = _API_INTENT_RELEVANCE.get(result.api_id, [])
            if intent in relevant_intents or any(intent in r for r in relevant_intents):
                s += 0.5

            return s

        return sorted(results, key=score, reverse=True)

    async def _summarize(
        self,
        message: str,
        intent_data: dict,
        history: list[dict],
        ranked_results: list[StepResult],
        ltm_history: list[dict] | None = None,
        db=None,
    ) -> str:
        filtered_results = _filter_results_by_question(message, ranked_results, db)
        success_filtered = [r for r in filtered_results if r.status == "success" and r.data]

        direct_format_apis = {
            "MOCK_RATE_SIMULATION",
            "MOCK_RATE_LOOKUP",
            "MOCK_PRODUCT_LOOKUP",
            "MOCK_DOCUMENT_SEARCH",
            "MOCK_ELIGIBILITY_CHECK",
            "MOCK_PERSONALIZED_RATE_LOOKUP",
            "MOCK_EXCHANGE_RATE_LOOKUP",
            "MOCK_CURRENCY_EXCHANGE_CALC",
            "MOCK_FOREIGN_REMITTANCE",
            "MOCK_FOREIGN_DEPOSIT_RATE",
            "MOCK_NOTIFICATION_RULES",
            "MOCK_NOTIFICATION_SEND",
        }
        if len(success_filtered) == 1 and success_filtered[0].api_id in direct_format_apis:
            return self._single_result_answer(success_filtered[0], message)

        filtered_ids = {r.api_id for r in success_filtered}
        if {"MOCK_ELIGIBILITY_CHECK", "MOCK_DOCUMENT_SEARCH"} <= filtered_ids:
            elg = next((r for r in success_filtered if r.api_id == "MOCK_ELIGIBILITY_CHECK"), None)
            doc = next((r for r in success_filtered if r.api_id == "MOCK_DOCUMENT_SEARCH"), None)
            return self._application_answer(elg, doc)

        if not self._llm_enabled:
            return self._template_answer(filtered_results if success_filtered else ranked_results)

        context_parts: list[str] = []
        for result in success_filtered:
            context_parts.append(
                f"[{result.api_id}]\n"
                f"{json.dumps(result.data, ensure_ascii=False, indent=2)}"
            )

        if not context_parts:
            return self._template_answer(filtered_results if filtered_results else ranked_results)

        context = "\n\n".join(context_parts)
        intent = intent_data.get("intent", INTENT_INQUIRY)
        intent_guide = {
            INTENT_INQUIRY: "Provide concise factual lookup results.",
            INTENT_COMPARISON: "Organize the answer as a comparison.",
            INTENT_RECOMMENDATION: "Recommend only with reasons supported by the tool results.",
            INTENT_APPLICATION: "Explain application guidance step by step.",
            INTENT_OTHER: "Answer clearly and cautiously.",
        }.get(intent, "Answer clearly and cautiously.")

        ltm_context = ""
        if ltm_history:
            past = ltm_history[-3:]
            summaries = "\n".join(
                f"  - [{h['intent']}] Q: {h['question'][:80]} / A: {h['answer'][:120]}"
                for h in past
            )
            ltm_context = (
                "\n\n[Past counseling summary]\n"
                f"{summaries}\n"
                "Use it only as supporting context and do not add new facts from it."
            )

        allowed_api_ids = [result.api_id for result in success_filtered]
        answer_schema = self._structured_answer_schema()
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        system_prompt = (
            "You are a financial support assistant.\n"
            "Return JSON only.\n"
            "Use only facts that appear in the provided tool results.\n"
            "Never invent rates, amounts, months, fees, payments, eligibility, policy, or document information.\n"
            "If information is missing from the tool results, write it under missing_information instead of guessing.\n"
            "Every bullet must contain source_api_id and must be grounded in that tool result.\n"
            "Do not compute or infer numbers that are not explicitly present in the tool results.\n"
            "If the repayment method is grace equal principal, do not claim a fixed monthly payment unless the tool result explicitly provides one.\n"
            f"Answer style: {intent_guide}\n"
            f"Allowed source_api_id values: {', '.join(allowed_api_ids)}\n"
            f"JSON schema: {json.dumps(answer_schema, ensure_ascii=False)}"
            f"{ltm_context}"
        )
        user_prompt = (
            f"Customer question: {message}\n\n"
            f"[Tool results]\n{context}\n\n"
            "Return JSON matching the schema. "
            "If a fact is not supported by the tool results, put that note in missing_information."
        )

        for attempt in range(2):
            retry_prompt = ""
            if attempt == 1:
                retry_prompt = (
                    "\nPrevious answer failed validation.\n"
                    "Retry with stricter grounding.\n"
                    "Every numeric bullet must match numbers present in the referenced source_api_id tool result.\n"
                    "If a numeric fact is missing, move it to missing_information instead of writing the bullet."
                )

            try:
                response = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt + retry_prompt,
                        },
                        *history[-8:],
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=512,
                )
                payload = json.loads(response.choices[0].message.content or "{}")
                validated = self._validate_structured_answer_payload(payload, success_filtered)
                if validated:
                    return self._render_structured_answer(validated)
            except Exception:
                if attempt == 1:
                    return self._template_answer(filtered_results if filtered_results else ranked_results)

        return self._template_answer(filtered_results if filtered_results else ranked_results)

    def _structured_answer_schema(self) -> dict:
        return {
            "summary": "string",
            "bullets": [
                {
                    "text": "string",
                    "source_api_id": "string",
                }
            ],
            "missing_information": ["string"],
            "disclaimer": "string",
        }

    def _validate_structured_answer_payload(
        self,
        payload: dict,
        results: list[StepResult],
    ) -> dict | None:
        if not isinstance(payload, dict):
            return None

        summary = " ".join(str(payload.get("summary", "")).split())
        disclaimer = " ".join(str(payload.get("disclaimer", "")).split())
        bullets = payload.get("bullets")
        missing_information = payload.get("missing_information", [])

        if not summary or not isinstance(bullets, list) or not isinstance(missing_information, list):
            return None

        tool_output_map: dict[str, dict] = {}
        for result in results:
            if result.status == "success" and result.data:
                tool_output_map[result.api_id] = {
                    "agent": None,
                    "data_text": json.dumps(result.data, ensure_ascii=False),
                    "summary": result.api_id,
                }

        if not tool_output_map:
            return None

        normalized_bullets: list[dict[str, str]] = []
        for item in bullets:
            if not isinstance(item, dict):
                return None
            text = " ".join(str(item.get("text", "")).split())
            source_api_id = str(item.get("source_api_id", "")).strip()
            if not text or not source_api_id or source_api_id not in tool_output_map:
                return None

            grounded, _, _, _ = _check_grounding(
                text,
                {source_api_id: tool_output_map[source_api_id]},
            )
            if not grounded:
                return None

            normalized_bullets.append(
                {
                    "text": text,
                    "source_api_id": source_api_id,
                }
            )

        normalized_missing = [
            " ".join(str(item).split())
            for item in missing_information
            if str(item).strip()
        ]

        return {
            "summary": summary,
            "bullets": normalized_bullets,
            "missing_information": normalized_missing,
            "disclaimer": disclaimer,
        }

    def _render_structured_answer(self, payload: dict) -> str:
        sections: list[str] = [payload["summary"]]

        for item in payload["bullets"]:
            sections.append(f"- {item['text']}")

        missing_information = payload.get("missing_information") or []
        if missing_information:
            sections.append("Missing information")
            for item in missing_information:
                sections.append(f"- {item}")

        disclaimer = payload.get("disclaimer", "").strip()
        if disclaimer:
            sections.append(f"* {disclaimer}")

        return "\n".join(sections)

    def _single_result_answer(self, result: StepResult, message: str = "") -> str:
        """단일 API 결과를 간결한 포맷으로 반환한다 (LLM 우회 — 데이터 범위를 초과한 LLM 응답 방지용)."""
        from app.agents.formatters import format_single
        text = format_single(result, message)
        if text:
            return text
        # 포맷터 미등록 API → 다중 포맷 fallback
        return self._template_answer([result])

    def _single_result_answer_legacy(self, result: StepResult, message: str = "") -> str:
        """[DEPRECATED] formatter 분리 전 인라인 구현 — 참조용으로 유지."""
        d = result.data or {}
        api = result.api_id

        if api == "MOCK_RATE_SIMULATION":
            principal = d.get("principal", 0)
            rate = d.get("annual_rate", 0)
            term = d.get("term_months", 0)
            method = d.get("method", "")
            total = d.get("total_payment", 0)
            interest = d.get("total_interest", 0)
            # 어떤 상품/등급 기준 금리인지 부제 생성 (message에 상품명이 있으면 표시)
            from app.agents.rate_agent import _extract_product_name, _extract_credit_grade
            _product = _extract_product_name(message) if message else None
            _grade = _extract_credit_grade(message) if message else None
            _rate_source = ""
            if _product:
                _grade_label = f"{_grade}등급 기준" if _grade else "신용등급 5등급(기본) 기준"
                _rate_source = f" ({_product} / {_grade_label})"

            if method == "거치식균등분할":
                grace = d.get("grace_months", 0)
                grace_monthly = d.get("grace_monthly_interest", 0)
                repay = d.get("repay_months", 0)
                repay_monthly = d.get("repay_monthly_payment", 0)
                return (
                    f"■ 금리 시뮬레이션 결과 (거치식 균등분할){_rate_source}\n"
                    f"  · 대출원금: {principal:,}원 / 연 {rate}% / {term}개월\n"
                    f"  · 거치 기간 {grace}개월: 월 이자 {grace_monthly:,}원\n"
                    f"  · 균등분할 {repay}개월: 월 납입금 {repay_monthly:,}원\n"
                    f"  · 총 이자: {interest:,}원\n"
                    f"  · 총 상환금액: {total:,}원"
                )

            # 거치식 원금균등상환은 월 납입금이 일정하지 않으므로
            # 거치 이자와 첫달/마지막달 상환금을 함께 안내한다.
            if method == "거치식원금균등상환":
                grace = d.get("grace_months", 0)
                grace_monthly = d.get("grace_monthly_interest", 0)
                repay = d.get("repay_months", 0)
                first_repay = d.get("first_repay_payment", 0)
                last_repay = d.get("last_repay_payment", 0)
                return (
                    f"■ 금리 시뮬레이션 결과 (거치식 원금균등상환){_rate_source}\n"
                    f"  · 대출원금: {principal:,}원 / 연 {rate}% / {term}개월\n"
                    f"  · 거치 기간 {grace}개월: 월 이자 {grace_monthly:,}원\n"
                    f"  · 원금균등 {repay}개월: 첫달 {first_repay:,}원 / 마지막달 {last_repay:,}원\n"
                    f"  · 총 이자: {interest:,}원\n"
                    f"  · 총 상환금액: {total:,}원"
                )

            monthly = d.get("monthly_payment", 0)
            return (
                f"■ 금리 시뮬레이션 결과{_rate_source}\n"
                f"  · 대출원금: {principal:,}원 / 연 {rate}% / {term}개월 ({method})\n"
                f"  · 월 납입금: {monthly:,}원\n"
                f"  · 총 이자: {interest:,}원\n"
                f"  · 총 상환금액: {total:,}원"
            )

        if api == "MOCK_RATE_LOOKUP":
            rates = d.get("rates", [])
            if not rates:
                return "금리 정보를 조회할 수 없었습니다."
            # 메시지에 특정 상품명이 언급된 경우 해당 상품만 표시
            # 조건: 메시지 단어(3자 이상)가 상품명 안에 포함되는 경우만 매칭
            # (역방향 — 상품명 단어를 메시지에서 찾는 방식은 "대출" 같은 짧은 단어가
            #  "신용대출" 안에 substring 매칭되어 모든 상품이 걸리는 버그가 있음)
            filtered_rates = [
                r for r in rates
                if any(kw in r.get("product_name", "") for kw in message.split()
                       if len(kw) >= 3)
            ]
            display_rates = filtered_rates if filtered_rates else rates
            title = "■ 금리 비교" if len(display_rates) > 1 else "■ 금리 안내"
            lines = [title]
            for r in display_rates:
                pref = r.get("max_preferential", 0)
                lines.append(
                    f"  · {r.get('product_name','')}: "
                    f"{r.get('min_final_rate','')}% ~ {r.get('max_final_rate','')}%"
                    + (f"  (우대금리 최대 {pref}%p 할인)" if pref else "")
                )
            return "\n".join(lines)

        if api == "MOCK_DOCUMENT_SEARCH":
            docs = d.get("documents", [])
            if not docs:
                return "서류 정보를 조회할 수 없었습니다."
            lines = ["■ 필요서류"]
            for doc in docs:
                lines.append(f"  · {doc.get('name','')}")
            return "\n".join(lines)

        if api == "MOCK_ELIGIBILITY_CHECK":
            eligible = d.get("eligible", False)
            product = d.get("product_name", "")
            rec = d.get("recommendation", "")
            est_rate = d.get("estimated_rate")
            issues: list = d.get("issues", [])
            warnings: list = d.get("warnings", [])

            status = "신청 가능합니다." if eligible else "신청 조건을 충족하지 않습니다."
            header = f"■ 자격 조건 ({product})" if product else "■ 자격 조건"
            # rec에 이미 status 내용이 포함돼 있으면 rec만 표시
            main_msg = rec if rec else status
            lines = [header, f"  · {main_msg}"]
            if est_rate:
                lines.append(f"  · 예상 적용 금리: 연 {est_rate}%")
            for w in warnings:
                lines.append(f"  ⚠ {w}")
            for issue in issues:
                lines.append(f"  ✗ {issue}")
            return "\n".join(lines)

        if api == "MOCK_PERSONALIZED_RATE_LOOKUP":
            grade = d.get("credit_grade", "?")
            grade_label = d.get("grade_label", "")
            rates_list: list[dict] = d.get("rates", [])
            if not rates_list:
                return f"신용등급 {grade}등급에 해당하는 대출 상품 금리 정보를 찾을 수 없습니다."
            header = f"■ 신용등급 {grade}등급({grade_label}) 맞춤 금리"
            lines = [header]
            for r in rates_list:
                lines.append(
                    f"  · {r.get('product_name','')}: 연 {r.get('min_rate','')}% ~ {r.get('max_rate','')}%"
                )
            note = d.get("note", "")
            if note:
                lines.append(f"\n  ※ {note}")
            return "\n".join(lines)

        if api == "MOCK_PRODUCT_LOOKUP":
            d_dict = d if isinstance(d, dict) else {}
            products: list[dict] = d_dict.get("products", [])
            if not products:
                return "상품 정보를 조회할 수 없었습니다."
            lines = ["■ 대출 상품 안내"]
            for p in products:
                limit: int = p.get("max_amount", 0)
                # 한도를 억/천만 단위로 변환 (나머지 포함)
                if limit >= 100000000:
                    eok = limit // 100000000
                    rem = (limit % 100000000) // 10000000
                    limit_str = f"{eok}억" + (f" {rem}천만" if rem else "")
                elif limit >= 10000000:
                    limit_str = f"{limit // 10000000}천만"
                else:
                    limit_str = f"{limit // 10000}만"
                # ~ 를 ' ~ '(공백 포함)로 변경 — 마크다운 취소선(~~) 오해석 방지
                lines.append(
                    f"  · {p.get('name','')}"
                    f" | 금리 {p.get('min_rate','')}% ~ {p.get('max_rate','')}%"
                    f" | 한도 {limit_str}원"
                )
            return "\n".join(lines)

        if api == "MOCK_EXCHANGE_RATE_LOOKUP":
            rates_list: list[dict] = d.get("rates", [])
            timestamp: str = d.get("timestamp", "")[:10]
            if not rates_list:
                return "환율 정보를 조회할 수 없었습니다."
            title = f"■ 주요 환율 ({timestamp} 기준)" if timestamp else "■ 주요 환율"
            lines = [title]
            for r in rates_list:
                change = r.get("change", 0)
                arrow = "▲" if change > 0 else ("▽" if change < 0 else "─")
                cur = r.get("currency", "")
                std = r.get("standard", "")
                buy = r.get("buy", "")
                sell = r.get("sell", "")
                lines.append(
                    f"  · {cur} ({r.get('name','')}): "
                    f"기준 {std}원  살때 {sell}원  팔때 {buy}원  {arrow}{abs(change)}원"
                )
            note = d.get("note", "")
            if note:
                lines.append(f"\n  ※ {note}")
            return "\n".join(lines)

        if api == "MOCK_CURRENCY_EXCHANGE_CALC":
            if not isinstance(d, dict):
                return "환전 계산 결과를 불러올 수 없습니다."
            from_c    = d.get("from_currency", "KRW")
            to_c      = d.get("to_currency", "")
            from_amt  = d.get("from_amount", 0)
            to_amt    = d.get("to_amount", 0)
            rate_app  = d.get("rate_applied", 0)
            fee       = d.get("fee_krw", 0)
            discount  = d.get("discount_rate", 0)
            note      = d.get("note", "")
            buy_rate  = d.get("buy_rate")   # 은행 살때 (고객이 외화 팔 때 적용)
            sell_rate = d.get("sell_rate")  # 은행 팔때 (고객이 외화 살 때 적용)
            std_rate     = d.get("standard_rate", 0)
            is_reverse   = d.get("is_reverse_calc", False)
            fx_code      = to_c if from_c == "KRW" else from_c
            lines = [f"■ 환전 계산 결과 ({from_c} → {to_c})"]
            if is_reverse:
                # 역산: "N달러 받으려면 원화 얼마?" 표시
                net_krw = round(to_amt * rate_app, 0)
                lines.append(f"  · 목표 수령 금액: {to_amt:,} {to_c}")
                lines.append(f"  · 기준 환율: {std_rate:,}원/{fx_code}")
                if buy_rate and sell_rate:
                    lines.append(f"  · 살때(고객 외화 매입): {sell_rate:,}원/{fx_code}")
                    lines.append(f"  · 팔때(고객 외화 매도): {buy_rate:,}원/{fx_code}")
                lines.append(f"  · 적용 환율: {rate_app:,}원/{fx_code}")
                lines.append(f"  · 환산 원화: {net_krw:,.0f}원  ({to_amt:,} {to_c} × {rate_app:,}원)")
                lines.append(f"  · 수수료 추가: +{fee:,}원 (우대율 {discount}% 적용)")
                lines.append(f"  · 필요 원화: {from_amt:,.0f} KRW")
            else:
                # 일반: 보내는 금액 기준 표시
                if from_c == "KRW":
                    gross_amt = round(from_amt / rate_app, 4) if rate_app else 0
                    gross_str = f"{gross_amt:,} {to_c}"
                else:
                    gross_amt = round(from_amt * rate_app, 0)
                    gross_str = f"{gross_amt:,.0f}원"
                lines.append(f"  · 환전 신청금액: {from_amt:,} {from_c}")
                lines.append(f"  · 기준 환율: {std_rate:,}원/{fx_code}")
                if buy_rate and sell_rate:
                    lines.append(f"  · 살때(고객 외화 매입): {sell_rate:,}원/{fx_code}")
                    lines.append(f"  · 팔때(고객 외화 매도): {buy_rate:,}원/{fx_code}")
                lines.append(f"  · 적용 환율: {rate_app:,}원/{fx_code}")
                lines.append(f"  · 환전 환산액: {gross_str}  ({from_amt:,} {from_c} × {rate_app:,}원)")
                lines.append(f"  · 수수료 차감: −{fee:,}원 (우대율 {discount}% 적용)")
                lines.append(f"  · 수령 금액: {to_amt:,} {to_c}")
            if note:
                lines.append(f"\n  ※ {note}")
            return "\n".join(lines)

        if api == "MOCK_FOREIGN_REMITTANCE":
            methods_list: list[dict] = d.get("methods", [])
            daily_limit  = d.get("daily_limit_usd", 0)
            fee_est      = d.get("fee_estimate_krw")
            caution      = d.get("caution", "")
            dest         = d.get("destination_country")
            lines = ["■ 해외송금 안내"]
            if dest:
                lines.append(f"  · 수취국: {dest.get('name','')} — {dest.get('notes','')}")
            lines.append(f"  · 1일 인터넷 송금 한도: ${daily_limit:,}")
            if fee_est:
                lines.append(f"  · 예상 수수료: {fee_est:,}원")
            if methods_list:
                for m in methods_list[:2]:
                    lines.append(f"  · {m.get('method','')}: {m.get('processing_time','')}")
            if caution:
                lines.append(f"\n  ⚠ {caution}")
            return "\n".join(lines)

        if api == "MOCK_FOREIGN_DEPOSIT_RATE":
            deposit_rates: list[dict] = d.get("deposit_rates", [])
            note = d.get("note", "")
            if not deposit_rates:
                return "외화예금 금리 정보를 조회할 수 없었습니다."
            lines = ["■ 외화예금 금리"]
            for r in deposit_rates:
                lines.append(
                    f"  · {r.get('currency','')} ({r.get('name','')}) — "
                    f"보통예금 {r.get('demand_rate','')}% / "
                    f"정기 6개월 {r.get('time_deposit_6m','')}% / "
                    f"정기 12개월 {r.get('time_deposit_12m','')}%"
                )
            if note:
                lines.append(f"\n  ※ {note}")
            return "\n".join(lines)

        if api == "MOCK_NOTIFICATION_RULES":
            rules_list: list[dict] = d.get("rules", [])
            if not rules_list:
                return "등록된 알림 규칙이 없습니다."
            lines = ["■ 알림 규칙 안내"]
            for r in rules_list:
                active_tag = "✓" if r.get("is_active") else "✗ (비활성)"
                lines.append(
                    f"  · [{r.get('trigger_type','')}] {r.get('name','')} "
                    f"— {r.get('channel','')} 채널 {active_tag}"
                )
                desc = r.get("description", "")
                if desc:
                    lines.append(f"    {desc}")
            return "\n".join(lines)

        if api == "MOCK_NOTIFICATION_SEND":
            status  = d.get("status", "")
            msg     = d.get("message", "")
            channel = d.get("channel", "")
            note    = d.get("note", "")
            lines = ["■ 알림 발송 결과"]
            lines.append(f"  · 상태: {status}")
            lines.append(f"  · 채널: {channel}")
            lines.append(f"  · 내용: {msg}")
            if note:
                lines.append(f"  ※ {note}")
            return "\n".join(lines)

        # 나머지 API는 기본 템플릿으로
        return self._template_answer([result])

    # ──────────────────────────────────────────────────────────────────
    # _single_result_answer_legacy 끝
    # ──────────────────────────────────────────────────────────────────

    def _application_answer(
        self,
        elg: "StepResult | None",
        doc: "StepResult | None",
    ) -> str:
        """신청 흐름 답변 — 자격조건 + 필요서류를 하나로 합쳐 안내한다."""
        sections: list[str] = []

        if elg and elg.data:
            d = elg.data
            eligible = d.get("eligible", False)
            status = "신청 가능합니다." if eligible else "신청 조건을 충족하지 않습니다."
            conditions = d.get("conditions", [])
            lines = [f"■ 자격 조건\n  · {status}"]
            for c in conditions:
                lines.append(f"  · {c}")
            sections.append("\n".join(lines))

        if doc and doc.data:
            docs = doc.data.get("documents", [])
            lines = ["■ 필요서류"]
            for item in docs:
                lines.append(f"  · {item.get('name','')}")
            sections.append("\n".join(lines))

        sections.append("■ 신청 방법\n  · 영업점 방문 또는 인터넷·모바일 뱅킹을 통해 신청하실 수 있습니다.")

        return "\n\n".join(sections)

    def _template_answer(self, results: list[StepResult]) -> str:
        """LLM 없이 동작하는 템플릿 기반 응답 (fallback) — 포맷터 패키지로 위임한다."""
        from app.agents.formatters import format_multi
        return format_multi(results)

    def _template_answer_legacy(self, results: list[StepResult]) -> str:
        """[DEPRECATED] formatter 분리 전 인라인 구현 — 참조용으로 유지."""
        success = [r for r in results if r.status == "success" and r.data]
        errors  = [r for r in results if r.status != "success"]

        if not results:
            return "요청하신 정보를 조회할 수 없었습니다. 다시 시도해 주세요."

        labels = {
            "MOCK_PRODUCT_LOOKUP":            "대출 상품",
            "MOCK_RATE_LOOKUP":               "금리",
            "MOCK_POLICY_LOOKUP":             "정책/약관",
            "MOCK_DOCUMENT_SEARCH":           "필요서류",
            "MOCK_RATE_SIMULATION":           "금리 시뮬레이션",
            "MOCK_ELIGIBILITY_CHECK":         "자격 조건",
            "MOCK_COUNSELING_HISTORY":        "상담 이력",
            "MOCK_BRANCH_LOOKUP":             "지점 정보",
            "MOCK_PERSONALIZED_RATE_LOOKUP":  "맞춤 금리",
            "MOCK_EXCHANGE_RATE_LOOKUP":      "환율",
            "MOCK_CURRENCY_EXCHANGE_CALC":    "환전 계산",
            "MOCK_FOREIGN_REMITTANCE":        "해외송금",
            "MOCK_FOREIGN_DEPOSIT_RATE":      "외화예금 금리",
            "MOCK_NOTIFICATION_RULES":        "알림 규칙",
            "MOCK_NOTIFICATION_SEND":         "알림 발송",
        }

        sections: list[str] = []

        for r in success:
            label = labels.get(r.api_id, r.api_id)
            data = r.data
            if not isinstance(data, dict):
                sections.append(f"■ {label}: 데이터 확인 완료")
                continue

            lines: list[str] = [f"■ {label}"]

            if r.api_id == "MOCK_RATE_LOOKUP":
                for rate in data.get("rates", [])[:5]:
                    name     = rate.get("product_name", "")
                    lo       = rate.get("min_final_rate", "")
                    hi       = rate.get("max_final_rate", "")
                    max_pref = rate.get("max_preferential", 0)
                    if name:
                        lines.append(f"  · {name}: {lo}% ~ {hi}%")
                        if max_pref:
                            lines.append(f"    (우대금리 최대 {max_pref}%p 할인 가능)")

            elif r.api_id == "MOCK_RATE_SIMULATION":
                example = data.get("example")
                if example:
                    lines.append(f"  · {example}")
                monthly = data.get("monthly_payment")
                grace_monthly = data.get("grace_monthly_interest")
                first_repay = data.get("first_repay_payment")
                last_repay = data.get("last_repay_payment")
                total_interest = data.get("total_interest")
                if monthly:
                    lines.append(f"  · 월 납입금: {monthly:,}원")
                elif grace_monthly is not None and first_repay is not None and last_repay is not None:
                    lines.append(f"  · 거치 기간 월 이자: {grace_monthly:,}원")
                    lines.append(f"  · 상환 구간: 첫달 {first_repay:,}원 / 마지막달 {last_repay:,}원")
                if total_interest:
                    lines.append(f"  · 총 이자: {total_interest:,}원")

            elif r.api_id == "MOCK_PRODUCT_LOOKUP":
                for prod in data.get("products", [])[:4]:
                    name  = prod.get("name", "")
                    lo    = prod.get("min_rate", "")
                    hi    = prod.get("max_rate", "")
                    limit = prod.get("max_amount")
                    if name:
                        rate_str  = f" ({lo}%~{hi}%)" if lo and hi else ""
                        limit_str = f" / 한도 {limit:,}원" if limit else ""
                        lines.append(f"  · {name}{rate_str}{limit_str}")

            elif r.api_id == "MOCK_POLICY_LOOKUP":
                for pol in data.get("policies", [])[:3]:
                    title   = pol.get("title", "")
                    content = pol.get("content", "")
                    if title:
                        lines.append(f"  · {title}")
                        if content:
                            lines.append(f"    {content[:100]}")

            elif r.api_id == "MOCK_DOCUMENT_SEARCH":
                for doc in data.get("documents", [])[:5]:
                    name = doc.get("name", "")
                    if name:
                        lines.append(f"  · {name}")

            elif r.api_id == "MOCK_ELIGIBILITY_CHECK":
                recommendation = data.get("recommendation", "")
                if recommendation:
                    lines.append(f"  · {recommendation}")
                for issue in data.get("issues", [])[:2]:
                    lines.append(f"  · ⚠ {issue}")

            elif r.api_id == "MOCK_COUNSELING_HISTORY":
                for h in data.get("histories", [])[:3]:
                    date  = h.get("counseling_date", "")
                    topic = h.get("topic", "")
                    if topic:
                        lines.append(f"  · [{date}] {topic}")

            elif r.api_id == "MOCK_PERSONALIZED_RATE_LOOKUP":
                grade = data.get("credit_grade", "?")
                label = data.get("grade_label", "")
                lines[0] = f"■ 신용등급 {grade}등급({label}) 맞춤 금리"
                for pr in data.get("rates", [])[:4]:
                    lines.append(
                        f"  · {pr.get('product_name','')}: "
                        f"연 {pr.get('min_rate','')}% ~ {pr.get('max_rate','')}%"
                    )

            elif r.api_id == "MOCK_EXCHANGE_RATE_LOOKUP":
                for er in data.get("rates", [])[:5]:
                    change = er.get("change", 0)
                    arrow = "▲" if change > 0 else ("▽" if change < 0 else "─")
                    cur = er.get("currency", "")
                    lines.append(
                        f"  · {cur} ({er.get('name','')}): "
                        f"기준 {er.get('standard','')}원  살때 {er.get('sell','')}원  팔때 {er.get('buy','')}원  {arrow}{abs(change)}원"
                    )

            elif r.api_id == "MOCK_CURRENCY_EXCHANGE_CALC":
                from_c   = data.get("from_currency", "")
                to_c     = data.get("to_currency", "")
                fx_c     = to_c if from_c == "KRW" else from_c
                from_amt = data.get("from_amount", 0)
                rate_app = data.get("rate_applied", 0)
                fee      = data.get("fee_krw", 0)
                buy_r    = data.get("buy_rate", "")
                sell_r   = data.get("sell_rate", "")
                if from_c == "KRW":
                    gross_str = f"{round(from_amt / rate_app, 4):,} {to_c}" if rate_app else ""
                else:
                    gross_str = f"{round(from_amt * rate_app, 0):,.0f}원"
                lines.append(f"  · 환전 신청금액: {from_amt:,} {from_c}")
                if buy_r and sell_r:
                    lines.append(f"  · 살때 {sell_r}원/{fx_c}  팔때 {buy_r}원/{fx_c}")
                lines.append(f"  · 적용 환율: {rate_app}원/{fx_c}")
                if gross_str:
                    lines.append(f"  · 환전 환산액: {gross_str}  ({from_amt:,} {from_c} × {rate_app}원)")
                lines.append(f"  · 수수료 차감: −{fee:,}원")
                lines.append(f"  · 수령 금액: {data.get('to_amount','')} {to_c}")

            elif r.api_id == "MOCK_FOREIGN_REMITTANCE":
                daily = data.get("daily_limit_usd", "")
                lines.append(f"  · 1일 송금 한도: ${daily:,}" if daily else "")
                for m in data.get("methods", [])[:2]:
                    lines.append(f"  · {m.get('method','')}: {m.get('processing_time','')}")

            elif r.api_id == "MOCK_FOREIGN_DEPOSIT_RATE":
                for dr in data.get("deposit_rates", [])[:4]:
                    lines.append(
                        f"  · {dr.get('currency','')} ({dr.get('name','')}): "
                        f"정기12개월 {dr.get('time_deposit_12m','')}%"
                    )

            elif r.api_id == "MOCK_NOTIFICATION_RULES":
                for rule in data.get("rules", [])[:4]:
                    lines.append(
                        f"  · [{rule.get('trigger_type','')}] {rule.get('name','')} "
                        f"— {rule.get('channel','')} 채널"
                    )

            elif r.api_id == "MOCK_NOTIFICATION_SEND":
                lines.append(f"  · 상태: {data.get('status','')}")
                lines.append(f"  · 내용: {data.get('message','')}")

            else:
                for k, v in list(data.items())[:3]:
                    if v and not isinstance(v, (list, dict)):
                        lines.append(f"  · {k}: {v}")

            if len(lines) == 1:
                lines.append("  · 데이터 확인 완료")
            sections.append("\n".join(lines))

        if errors:
            failed = [labels.get(r.api_id, r.api_id) for r in errors]
            sections.append(f"⚠ 조회 실패: {', '.join(failed)}")

        if not sections:
            return "조회를 완료했으나 반환된 데이터가 없습니다."

        disclaimer = "\n\n※ 본 안내는 참고 목적이며, 실제 금융 상품 조건은 영업점 또는 공식 앱에서 반드시 확인하시기 바랍니다."
        return "\n\n".join(sections) + disclaimer

    # ─────────────────────────────────────────────────────────────
    # v2 Decision Graph 메서드
    # ─────────────────────────────────────────────────────────────

    def _classify_concepts(
        self,
        detected: list[str],
        all_concepts: list[str],
        detected_set: set[str],
    ) -> ClassifiedConcepts:
        """
        탐지된 Concept를 Core/Supporting/Reference로 분류한다.

        분류 방식:
        1. CONCEPT_CATEGORY_HINT로 해당 Concept의 '기본 카테고리'를 결정한다.
        2. confidence가 해당 카테고리의 threshold를 충족하면 그 카테고리로 분류한다.
        3. threshold 미달 시 한 단계 낮은 카테고리로 강등(demoted_from 기록)한다.
        4. 모든 threshold 미달이면 제외한다.
        5. hint 없는 Concept는 confidence로 직접 결정한다.

        직접 탐지 confidence: CONFIDENCE_DIRECT (0.90)
        온톨로지 확장 confidence: CONFIDENCE_EXPANDED (0.70)
        """
        core: list[ConceptItem] = []
        supporting: list[ConceptItem] = []
        reference: list[ConceptItem] = []

        _category_order = [ConceptCategory.CORE, ConceptCategory.SUPPORTING, ConceptCategory.REFERENCE]

        for cid in all_concepts:
            is_direct = cid in detected_set
            confidence = CONFIDENCE_DIRECT if is_direct else CONFIDENCE_EXPANDED
            t = get_threshold(cid)
            hint = CONCEPT_CATEGORY_HINT.get(cid)
            stage = "직접 탐지" if is_direct else "온톨로지 확장"

            demoted_from = None
            promoted_from = None

            if hint:
                # hint가 기대하는 카테고리부터 내려가며 threshold 충족 여부 확인
                category = None
                target_cats = _category_order[_category_order.index(hint):]
                for cat in target_cats:
                    if confidence >= t[cat.value]:
                        category = cat
                        break
                if category is None:
                    continue  # 모든 threshold 미달 → 제외

                if category != hint:
                    demoted_from = hint  # 기대 카테고리보다 낮게 분류됨
            else:
                category = classify_concept(cid, confidence)
                if category is None:
                    continue

            threshold = t[category.value]
            item = ConceptItem(
                name=cid,
                category=category,
                confidence=confidence,
                threshold=threshold,
                reason=f"{stage} — confidence {confidence:.2f} ≥ threshold {threshold:.2f}",
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

    def _evaluate_decision_rules(
        self,
        classified: ClassifiedConcepts,
        routed_agents: list[str],
        all_agents: list[str],
        intent_keywords: list[str],
    ) -> tuple[list[dict], list[SelectedAgentV2], list[RejectedAgentV2]]:
        """
        DECISION_RULES를 Concept 분류 결과에 대입해 Agent 선택/미선택 목록과 트리거된 룰을 반환한다.

        반환: (triggered_rules, selected_agents_v2, rejected_agents_v2)
        - triggered_rules: DecisionRule dict 목록 (DB 직렬화용)
        - selected_agents_v2: 선택된 Agent v2 목록
        - rejected_agents_v2: 미선택 Agent v2 목록
        """
        triggered_rules: list[dict] = []
        selected_map: dict[str, SelectedAgentV2] = {}

        core_names      = {item.name for item in classified.core}
        supporting_names = {item.name for item in classified.supporting}
        reference_names  = {item.name for item in classified.reference}

        for rule in DECISION_RULES:
            trigger_concept  = rule.get("trigger_concept")
            trigger_category = rule.get("trigger_category")
            required_agent   = rule.get("required_agent")

            # 트리거 Concept 없는 룰 = 기본 정책 (항상 triggered=True)
            if trigger_concept is None:
                triggered_rules.append(
                    {"rule_id": rule["rule_id"], "rule_name": rule["rule_name"], "triggered": True}
                )
                continue

            triggered = False
            if trigger_category == ConceptCategory.CORE       and trigger_concept in core_names:
                triggered = True
            elif trigger_category == ConceptCategory.SUPPORTING and trigger_concept in supporting_names:
                triggered = True
            elif trigger_category == ConceptCategory.REFERENCE  and trigger_concept in reference_names:
                triggered = True

            triggered_rules.append(
                {"rule_id": rule["rule_id"], "rule_name": rule["rule_name"], "triggered": triggered}
            )

            if not triggered or not required_agent:
                continue

            # 해당 Concept의 confidence를 score로 사용
            all_items = classified.all_concepts()
            concept_item = next((c for c in all_items if c.name == trigger_concept), None)
            score = concept_item.confidence if concept_item else 0.7

            if required_agent not in selected_map:
                selected_map[required_agent] = SelectedAgentV2(
                    agent_name=required_agent,
                    role=rule.get("role") or "general",
                    score=score,
                    reason=f"{rule['rule_name']} 트리거됨",
                    execution_mode=(
                        rule.get("execution_mode")
                        or ("lightweight" if required_agent == "PRODUCT_AGENT" else "normal")
                    ),
                    tools=list(rule.get("tools") or []),
                    depends_on=(
                        []
                        if required_agent in AGENT_SERIAL_PREREQUISITE
                        else AGENT_SERIAL_PREREQUISITE
                    ),
                )
            else:
                # 이미 선택된 Agent의 score는 최댓값으로 갱신
                existing = selected_map[required_agent]
                if score > existing.score:
                    selected_map[required_agent] = SelectedAgentV2(
                        **{**existing.model_dump(), "score": score}
                    )

        selected_agents: list[SelectedAgentV2] = list(selected_map.values())
        selected_names = {a.agent_name for a in selected_agents}

        # SEARCH_AGENT 키워드 트리거 확인
        query_str = " ".join(intent_keywords)
        if any(kw in query_str for kw in SEARCH_AGENT_TRIGGER_KEYWORDS):
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

        # 미선택 Agent 목록 구성
        rejected_agents: list[RejectedAgentV2] = []
        for agent_name in all_agents:
            if agent_name in selected_names:
                continue
            if agent_name == "SEARCH_AGENT":
                reason = (
                    "DOCUMENT_SEARCH는 POLICY_AGENT 내부 Tool로 처리 가능. "
                    "상담이력 조회 키워드 미감지."
                )
                score = 0.41
            else:
                reason = f"{agent_name} 담당 Concept가 Core/Supporting으로 분류되지 않음"
                score = 0.20
            rejected_agents.append(RejectedAgentV2(agent_name=agent_name, score=score, reason=reason))

        return triggered_rules, selected_agents, rejected_agents

    def _build_decision_v2(
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
        """
        run() 완료 후 수집된 모든 v2 데이터를 LeaderDecisionV2 스키마로 조립한다.
        """
        rules = [
            DecisionRule(
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                triggered=r["triggered"],
            )
            for r in triggered_rules
        ]

        core_names       = [c.name for c in classified.core]
        supporting_names = [c.name for c in classified.supporting]

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
                    "OPENAI_API_KEY 미설정 — 템플릿 모드 동작"
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
                f"선택 Agent: {[a.agent_name for a in selected_agents_v2]}."
            ),
            answer_slots=answer_slots or [],
            slot_rankings=slot_rankings or [],
            risk_flags=risk_flags or [],
            actions_taken=actions_taken or [],
            requires_disclaimer=requires_disclaimer,
        )

    def _extract_answer_slots(self, classified: ClassifiedConcepts) -> list[AnswerSlot]:
        """
        Core + Supporting Concept에서 Answer Slot을 생성한다.

        SLOT_CONCEPT_MAP을 역방향으로 사용해 concept_id → slot_name을 매핑한다.
        Reference Concept은 배경 컨텍스트이므로 슬롯 생성에서 제외한다.
        같은 slot_name에 여러 Concept이 매핑되면 슬롯 1개만 생성한다.
        """
        # concept_id → slot_name 역방향 맵 빌드
        concept_to_slot: dict[str, str] = {}
        for slot_name, cids in SLOT_CONCEPT_MAP.items():
            for cid in cids:
                if cid not in concept_to_slot:
                    concept_to_slot[cid] = slot_name

        target_items = classified.core + classified.supporting
        seen_slots: set[str] = set()
        slots: list[AnswerSlot] = []

        for item in target_items:
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

