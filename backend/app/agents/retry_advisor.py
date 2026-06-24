"""retry_advisor.py — Gate별 재시도·보강 전략 실행기.

LeaderAgent가 Gate 경고를 받았을 때 호출하는 두 개의 async 메서드를 제공한다.
  - retry_failed_tools : Tool 실패/빈 결과 재시도 (remove_params → alt_api)
  - rewrite_for_gate1  : Gate 1 WARNING 시 Concept 보강 (expand_synonyms → rewrite_query)

모든 시도는 RetryStrategyService를 통해 strategy_outcome_log에 기록된다.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from sqlalchemy.orm import Session
    from app.agents.base_agent import AgentOutput

from app.services.strategy_service import RetryStrategyService

# Tool 실패 시 대체 API 맵
_API_FALLBACK: dict[str, str] = {
    "MOCK_PERSONALIZED_RATE_LOOKUP": "MOCK_RATE_LOOKUP",
    "MOCK_CURRENCY_EXCHANGE_CALC":   "MOCK_EXCHANGE_RATE_LOOKUP",
    "MOCK_ELIGIBILITY_CHECK":        "MOCK_PRODUCT_LOOKUP",
}

_MAX_TOOLS_PER_REQUEST = 3   # 한 요청에서 재시도를 시도할 최대 Tool 수
_LLM_REWRITE_MODEL     = "gpt-4o-mini"  # 동의어 추출용 경량 모델


class RetryAdvisor:
    """요청별 재시도 전략 실행기. leader.run() 마다 새 인스턴스로 사용한다."""

    # ── Tool 재시도 ──────────────────────────────────────────────────────────

    async def retry_failed_tools(
        self,
        db: "Session",
        request_id: str,
        agent_output: "AgentOutput",
        intent: str,
        concept_ids: list[str],
    ) -> "AgentOutput":
        """실패하거나 데이터가 없는 Tool 결과를 재시도해 agent_output을 in-place 개선한다.

        전략 순서:
          1. remove_params  : params={} 로 동일 API 재호출 (mock-api 기본값 동작)
          2. alt_api        : _API_FALLBACK 에 등록된 대체 API 호출

        각 전략 시도는 strategy_outcome_log에 기록된다.
        """
        from app.tools.tool_gateway import invoke_tool

        best_strategies = RetryStrategyService.get_best_strategy(
            db, "tool_error", intent, concept_ids
        )

        tools_retried = 0

        for api_res in agent_output.api_results:
            if tools_retried >= _MAX_TOOLS_PER_REQUEST:
                break

            is_failed = api_res.get("status") != "success"
            is_empty  = not api_res.get("data")

            if not (is_failed or is_empty):
                continue

            api_id       = api_res["api_id"]
            trigger_gate = "tool_error" if is_failed else "tool_empty"

            improved = False
            for strategy in best_strategies:
                if improved:
                    break

                if strategy == "remove_params":
                    t0     = time.perf_counter()
                    log_id = RetryStrategyService.log_attempt(
                        db, request_id, trigger_gate, "remove_params",
                        api_id=api_id, intent=intent, concept_ids=concept_ids,
                    )
                    try:
                        result = await invoke_tool(db, api_id, params={})
                        latency = int((time.perf_counter() - t0) * 1000)
                        if result.status == "success" and result.data:
                            api_res["status"]     = "success"
                            api_res["data"]       = result.data
                            api_res["latency_ms"] = latency
                            api_res.pop("error", None)
                            RetryStrategyService.update_outcome(
                                db, log_id, "success", confidence_after=1.0, latency_ms=latency
                            )
                            improved = True
                        else:
                            RetryStrategyService.update_outcome(
                                db, log_id, "failed", latency_ms=latency,
                                error_detail=result.error or "empty data after remove_params",
                            )
                    except Exception as exc:
                        RetryStrategyService.update_outcome(
                            db, log_id, "failed", error_detail=str(exc)
                        )

                elif strategy == "alt_api":
                    fallback_id = _API_FALLBACK.get(api_id)
                    if not fallback_id:
                        continue
                    t0     = time.perf_counter()
                    log_id = RetryStrategyService.log_attempt(
                        db, request_id, trigger_gate, "alt_api",
                        api_id=api_id, intent=intent, concept_ids=concept_ids,
                    )
                    try:
                        result = await invoke_tool(db, fallback_id, params={})
                        latency = int((time.perf_counter() - t0) * 1000)
                        if result.status == "success" and result.data:
                            api_res["status"]     = "success"
                            api_res["data"]       = result.data
                            api_res["latency_ms"] = latency
                            api_res.pop("error", None)
                            RetryStrategyService.update_outcome(
                                db, log_id, "success", confidence_after=0.9, latency_ms=latency
                            )
                            improved = True
                        else:
                            RetryStrategyService.update_outcome(
                                db, log_id, "failed", latency_ms=latency,
                                error_detail=result.error or "empty data after alt_api",
                            )
                    except Exception as exc:
                        RetryStrategyService.update_outcome(
                            db, log_id, "failed", error_detail=str(exc)
                        )

            tools_retried += 1

        return agent_output

    # ── Gate 1 개념 보강 ─────────────────────────────────────────────────────

    async def rewrite_for_gate1(
        self,
        db: "Session",
        request_id: str,
        message: str,
        concept_trace_rows: list[dict],
        intent_data: dict,
        llm_client: "AsyncOpenAI | None",
    ) -> list[str]:
        """Gate 1 WARNING 후 추가 Concept ID를 찾아 반환한다.

        전략 순서:
          1. expand_synonyms : source_text 기반 ILIKE 검색 (LLM 불필요)
          2. rewrite_query   : LLM에 동의어 2-3개 요청 후 재탐지 (confidence < 0.5 항목이 있을 때)

        이미 탐지된 Concept는 제외한다.
        """
        from app.knowledge.concept_service import (
            detect_concepts_in_message,
            search_concepts,
        )

        existing_ids: set[str] = {row["concept_id"] for row in concept_trace_rows}
        low_conf_rows = [r for r in concept_trace_rows if (r.get("confidence") or 1.0) < 0.7]

        if not low_conf_rows:
            return []

        new_ids: list[str] = []
        intent = intent_data.get("intent")

        # ── 전략 1: expand_synonyms ──────────────────────────────────────
        for row in low_conf_rows:
            source_text = row.get("source_text") or ""
            if not source_text:
                # source_text 없으면 concept_id에서 키워드 추출
                cid = row.get("concept_id", "")
                source_text = cid.replace("CONCEPT_", "").replace("_", " ").lower()
            if not source_text:
                continue

            log_id = RetryStrategyService.log_attempt(
                db, request_id, "gate1_warn", "expand_synonyms",
                api_id=None, intent=intent,
                concept_ids=[row.get("concept_id", "")],
            )
            t0 = time.perf_counter()
            try:
                found = search_concepts(db, source_text)
                latency = int((time.perf_counter() - t0) * 1000)
                added = [c.concept_id for c in found if c.concept_id not in existing_ids]
                for cid in added:
                    if cid not in new_ids:
                        new_ids.append(cid)
                outcome = "success" if added else "no_change"
                RetryStrategyService.update_outcome(
                    db, log_id, outcome, latency_ms=latency
                )
            except Exception as exc:
                RetryStrategyService.update_outcome(
                    db, log_id, "failed", error_detail=str(exc)
                )

        # ── 전략 2: rewrite_query (LLM 필요, confidence < 0.5 일 때만) ──
        very_low = [r for r in low_conf_rows if (r.get("confidence") or 1.0) < 0.5]
        if llm_client and very_low:
            labels = [r.get("source_text") or r.get("concept_id", "") for r in very_low]
            labels_str = ", ".join(l for l in labels if l)

            log_id = RetryStrategyService.log_attempt(
                db, request_id, "gate1_warn", "rewrite_query",
                api_id=None, intent=intent, concept_ids=list(existing_ids),
            )
            t0 = time.perf_counter()
            try:
                resp = await llm_client.chat.completions.create(
                    model=_LLM_REWRITE_MODEL,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=80,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "금융 도메인 전문가다. "
                                "주어진 한국어 금융 용어에 대해 동의어·유사어 2~3개를 "
                                'JSON {"terms": [...]} 형식으로 반환한다.'
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"다음 용어의 동의어·유사어를 알려줘: {labels_str}",
                        },
                    ],
                )
                latency = int((time.perf_counter() - t0) * 1000)
                import json as _json
                payload = _json.loads(resp.choices[0].message.content or "{}")
                terms: list[str] = payload.get("terms", [])
                added: list[str] = []
                for term in terms:
                    for concept in detect_concepts_in_message(db, term):
                        if concept.concept_id not in existing_ids and concept.concept_id not in new_ids:
                            new_ids.append(concept.concept_id)
                            added.append(concept.concept_id)
                outcome = "success" if added else "no_change"
                RetryStrategyService.update_outcome(
                    db, log_id, outcome, latency_ms=latency
                )
            except Exception as exc:
                RetryStrategyService.update_outcome(
                    db, log_id, "failed", error_detail=str(exc)
                )

        return new_ids
