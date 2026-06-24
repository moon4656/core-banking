# graph_builder.py — Leader Agent Decision Graph 노드/엣지 빌더
#
# GraphContext: 요청 1건의 판단 과정을 노드/엣지로 누적한 뒤 flush()로 DB에 일괄 저장한다.
# Leader Agent는 _build_graph() 메서드에서만 이 클래스를 사용한다.
#
# 실패 격리: flush()는 try/except로 감싸며, 그래프 저장 실패가 서비스 응답을 막으면 안 된다.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.trace_model import LeaderDecisionEdge, LeaderDecisionNode
from app.core.config import settings

# Sub-Agent 가로 열 배치 — 순서 보장
_AGENT_ORDER = ["PRODUCT_AGENT", "RATE_AGENT", "POLICY_AGENT", "SEARCH_AGENT"]

# 노드 타입별 기본 y 위치 (픽셀 단위, React Flow 기준)
_ROW_Y: dict[str, int] = {
    "USER_QUERY":       0,
    "MEMORY_HINT":      120,
    "INTENT":           240,
    "CONCEPT":          380,
    "LEADER_DECISION":  520,
    "SUB_AGENT":        660,
    "TOOL_CALL":        800,
    "RERANKING_SCORE":  940,
    "FINAL_RESPONSE":   1080,
    "MEMORY_WRITE":     1220,
}


@dataclass
class GraphContext:
    """요청 1건의 Decision Graph 상태를 메모리에 누적한다."""

    request_id: str
    _nodes: list[dict] = field(default_factory=list)
    _edges: list[dict] = field(default_factory=list)
    _seq: int = 0
    _edge_counter: dict[str, int] = field(default_factory=dict)

    def _next_node_id(self, node_type: str) -> str:
        self._seq += 1
        short = self.request_id.replace("-", "")[:8]
        return f"node_{node_type.lower()}_{short}_{self._seq:03d}"

    def _next_edge_id(self, edge_type: str, src_suffix: str, tgt_suffix: str) -> str:
        short = self.request_id.replace("-", "")[:8]
        base = f"edge_{edge_type.lower()}_{short}_{src_suffix}_{tgt_suffix}"
        count = self._edge_counter.get(base, 0) + 1
        self._edge_counter[base] = count
        return base if count == 1 else f"{base}_{count}"

    def _auto_position(self, node_type: str, col_index: int = 0) -> tuple[float, float]:
        y = float(_ROW_Y.get(node_type, 0))
        x_spacing = 180.0
        if node_type == "CONCEPT":
            x_spacing = 240.0
        elif node_type in {"SUB_AGENT", "TOOL_CALL"}:
            x_spacing = 220.0
        x = 400.0 + col_index * x_spacing
        return x, y

    def add_node(
        self,
        node_type: str,
        label: str,
        data: dict[str, Any],
        status: str = "SUCCESS",
        duration_ms: int | None = None,
        col_index: int = 0,
    ) -> str:
        node_id = self._next_node_id(node_type)
        x, y = self._auto_position(node_type, col_index)
        self._nodes.append({
            "node_id":        node_id,
            "node_type":      node_type,
            "node_label":     label,
            "status":         status,
            "sequence_order": self._seq,
            "position_x":     x,
            "position_y":     y,
            "data":           data,
            "duration_ms":    duration_ms,
        })
        return node_id

    def add_edge(
        self,
        edge_type: str,
        source_node_id: str,
        target_node_id: str,
        label: str | None = None,
        data: dict[str, Any] | None = None,
        weight: float = 1.0,
    ) -> str:
        src_suffix = source_node_id.split("_")[-1]
        tgt_suffix = target_node_id.split("_")[-1]
        edge_id = self._next_edge_id(edge_type, src_suffix, tgt_suffix)
        self._edges.append({
            "edge_id":        edge_id,
            "edge_type":      edge_type,
            "edge_label":     label,
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "data":           data or {},
            "weight":         weight,
        })
        return edge_id

    def flush(self, db: Session) -> None:
        """누적된 노드/엣지를 DB에 일괄 저장한다. 실패해도 롤백 후 조용히 반환."""
        try:
            for n in self._nodes:
                db.add(LeaderDecisionNode(request_id=self.request_id, **n))
            for e in self._edges:
                db.add(LeaderDecisionEdge(request_id=self.request_id, **e))
            db.commit()
        except Exception:
            db.rollback()


def build_decision_graph(
    db: Session,
    *,
    request_id: str,
    message: str,
    session_id: str | None,
    memory_turns: int,
    ltm_turns: int,
    intent_data: dict,
    intent_ms: int,
    detected: list[str],
    all_concepts: list[str],
    detected_set: set[str],
    route_result: Any,          # AgentRouteResponse
    routed_agents: list[str],
    agent_api_results: dict[str, list[dict]],   # agent_id → [api_res, ...]
    agent_latencies: dict[str, int],            # agent_id → total latency ms
    ranked_results: list[Any],  # list[StepResult]
    answer: str,
    confidence: float,
    llm_enabled: bool,
    short_memory_save: dict[str, Any] | None = None,
    long_term_memory_save: dict[str, Any] | None = None,
) -> None:
    """
    Leader Agent 실행 완료 후 Decision Graph를 구성해 DB에 저장한다.

    실패 시 flush() 내부에서 롤백하며 예외를 외부로 전파하지 않는다.
    """
    gc = GraphContext(request_id=request_id)

    # ── 1. UserQuery ──────────────────────────────────────
    n_query = gc.add_node("USER_QUERY", "채팅 요청", {
        "message":    message,
        "session_id": session_id or "",
    })

    # ── 2. MemoryHint (Short) ─────────────────────────────
    n_mem_short = gc.add_node("MEMORY_HINT", "Short Memory", {
        "memory_type":  "SHORT",
        "turns_loaded": memory_turns,
    }, col_index=-2)

    # ── 3. MemoryHint (LTM) ───────────────────────────────
    n_mem_ltm = gc.add_node("MEMORY_HINT", "Long-term Memory", {
        "memory_type":  "LTM",
        "turns_loaded": ltm_turns,
    }, col_index=-1)

    # ── 4. Intent ─────────────────────────────────────────
    n_intent = gc.add_node("INTENT", "의도 분석", {
        "intent_code": intent_data.get("intent"),
        "confidence":  intent_data.get("confidence", 0.9),
        "keywords":    intent_data.get("keywords", []),
        "urgency":     intent_data.get("urgency", "low"),
        "reason": (
            f"키워드 {intent_data.get('keywords', [])} 분석 → "
            f"{intent_data.get('intent', 'INQUIRY')} 분류"
        ),
    }, duration_ms=intent_ms)

    gc.add_edge("HAS_INTENT", n_query, n_intent,
                data={"confidence": intent_data.get("confidence", 0.9)})
    gc.add_edge("INFLUENCES", n_mem_short, n_intent,
                data={"memory_type": "SHORT", "turns_used": memory_turns})
    if ltm_turns > 0:
        gc.add_edge("INFLUENCES", n_mem_ltm, n_intent,
                    data={"memory_type": "LTM", "turns_used": ltm_turns})

    # ── 5. Concept 노드 ───────────────────────────────────
    concept_nodes: dict[str, str] = {}  # concept_id → node_id
    expanded_ids = [c for c in all_concepts if c not in detected_set]
    total_concept_count = len(detected) + len(expanded_ids)
    center_offset = (total_concept_count - 1) / 2 if total_concept_count else 0

    for i, cid in enumerate(detected):
        n = gc.add_node("CONCEPT", cid, {
            "concept_id":     cid,
            "detection_type": "DIRECT",
            "source_keyword": cid.replace("CONCEPT_", "").lower(),
            "weight":         1.0,
        }, col_index=round(i - center_offset))
        concept_nodes[cid] = n
        gc.add_edge("DETECTS", n_query, n,
                    data={"detection_type": "DIRECT", "weight": 1.0})

    for i, cid in enumerate(expanded_ids):
        n = gc.add_node("CONCEPT", cid, {
            "concept_id":     cid,
            "detection_type": "EXPANDED",
            "weight":         0.6,
        }, col_index=round(len(detected) + i - center_offset))
        concept_nodes[cid] = n
        gc.add_edge("DETECTS", n_query, n,
                    label="확장",
                    data={"detection_type": "EXPANDED", "weight": 0.6})

    # ── 6. LeaderDecision ─────────────────────────────────
    n_leader = gc.add_node("LEADER_DECISION", "LeaderDecision", {
        "detected_intent":   intent_data.get("intent"),
        "all_concept_ids":   all_concepts,
        "selected_agent_ids": routed_agents,
        "confidence_score":  confidence,
        "total_concepts":    len(all_concepts),
    })

    for cid in all_concepts:
        if cid in concept_nodes:
            gc.add_edge("HANDLED_BY", concept_nodes[cid], n_leader,
                        data={"concept_id": cid})

    # ── 7. SubAgent 노드 (선택 + 미선택 전체) ──────────────
    agent_nodes: dict[str, str] = {}
    route_map: dict[str, list[str]] = {
        ri.agent_id: ri.concept_ids for ri in route_result.routing
    }

    for i, agent_id in enumerate(_AGENT_ORDER):
        is_selected = agent_id in routed_agents
        status = "SELECTED" if is_selected else "SKIPPED"
        concept_ids = route_map.get(agent_id, [])
        n = gc.add_node("SUB_AGENT", agent_id, {
            "agent_id":   agent_id,
            "status":     status,
            "concept_ids": concept_ids,
            "reason": (
                f"{concept_ids} 매핑으로 선택" if is_selected else "미선택"
            ),
        }, status=status, col_index=i - 1)
        agent_nodes[agent_id] = n
        gc.add_edge("SELECTS", n_leader, n, data={
            "status":          status,
            "concept_coverage": len(concept_ids),
        })

    # ── 8. ToolCall 노드 ──────────────────────────────────
    tool_nodes: dict[str, str] = {}  # api_id → node_id

    # 각 Tool을 부모 Agent의 col_index 기준으로 배치한다.
    # Agent가 여러 Tool을 가질 경우 해당 Agent col 주변으로 좌우 분산.
    # → Agent와 Tool 사이의 엣지가 교차하지 않고 수직으로 정렬된다.
    agent_col_map: dict[str, int] = {
        aid: _AGENT_ORDER.index(aid) - 1
        for aid in _AGENT_ORDER
        if aid in routed_agents
    }

    for agent_id in routed_agents:
        agent_col = agent_col_map.get(agent_id, 0)
        tools = agent_api_results.get(agent_id, [])
        n_tools = len(tools)
        n_agent = agent_nodes.get(agent_id)

        for local_j, api_res in enumerate(tools):
            # Tool이 1개면 Agent 정중앙, 여러 개면 Agent col 기준으로 좌우 분산
            offset = local_j - (n_tools - 1) / 2.0
            tool_col = int(agent_col + offset + (0.5 if offset >= 0 else -0.5))

            api_id = api_res.get("api_id", "UNKNOWN")
            ok     = api_res.get("status") == "success"
            status = "SUCCESS" if ok else "FAILED"
            n_tool = gc.add_node("TOOL_CALL", api_id, {
                "tool_id":          api_id,
                "agent_id":         agent_id,
                "status":           status,
                "duration_ms":      api_res.get("latency_ms"),
                "error_message":    api_res.get("error"),
                "response_summary": f"{api_id} {'성공' if ok else '실패'}",
            }, status=status, duration_ms=api_res.get("latency_ms"),
               col_index=tool_col)

            if api_id not in tool_nodes:
                tool_nodes[api_id] = n_tool

            if n_agent:
                gc.add_edge("CALLS", n_agent, n_tool, data={
                    "tool_id": api_id,
                    "status":  status,
                })

    # ── 9. ReRankingScore 노드 ────────────────────────────
    if ranked_results:
        ranked_api_ids = [r.api_id for r in ranked_results]
        n_rerank = gc.add_node("RERANKING_SCORE", "Re-ranking", {
            "ranked_order": ranked_api_ids,
            "top":          ranked_api_ids[0] if ranked_api_ids else None,
        })
        for rank, r in enumerate(ranked_results):
            src = tool_nodes.get(r.api_id)
            if src:
                gc.add_edge("SCORED_BY", src, n_rerank, data={
                    "rank":   rank + 1,
                    "status": r.status,
                }, weight=1.0 / (rank + 1))
    else:
        n_rerank = None

    # ── 10. FinalResponse ─────────────────────────────────
    n_response = gc.add_node("FINAL_RESPONSE", "최종 답변", {
        "answer_length":    len(answer),
        "llm_model":        settings.OPENAI_MODEL if llm_enabled else "template",
        "intent_applied":   intent_data.get("intent"),
        "template_fallback": not llm_enabled,
    })
    gc.add_edge("PRODUCES", n_leader, n_response, data={
        "intent_applied":     intent_data.get("intent"),
        "evidence_count_used": len(tool_nodes),
    })

    # 상위 2개 결과가 최종 답변을 support
    for rank, r in enumerate(ranked_results[:2]):
        src = tool_nodes.get(r.api_id)
        if src and r.status == "success":
            weight = 0.5 if rank == 0 else 0.35
            gc.add_edge("SUPPORTS", src, n_response, data={
                "contribution_weight": weight,
                "rank": rank + 1,
            }, weight=weight)

    # ── 저장 ──────────────────────────────────────────────
    memory_writes = [
        ("SHORT", short_memory_save or {}, -1),
        ("LTM", long_term_memory_save or {}, 1),
    ]
    for memory_type, payload, col_index in memory_writes:
        if not payload:
            continue
        is_short = memory_type == "SHORT"
        n_memory_write = gc.add_node(
            "MEMORY_WRITE",
            "Short Memory Save" if is_short else "Long-term Memory Save",
            {
                "memory_type": memory_type,
                "saved": payload.get("saved", False),
                "stored_turns": payload.get("stored_turns"),
                "turn_index": payload.get("turn_index"),
                "question_summary": payload.get("question_summary"),
                "answer_summary": payload.get("answer_summary"),
                "preview": payload.get("preview", []),
                "reason": payload.get("reason"),
            },
            status="SUCCESS" if payload.get("saved") else "FAILED",
            col_index=col_index,
        )
        gc.add_edge(
            "SAVES_MEMORY",
            n_response,
            n_memory_write,
            label="save",
            data={"memory_type": memory_type},
        )

    gc.flush(db)
