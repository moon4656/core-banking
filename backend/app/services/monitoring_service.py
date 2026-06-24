"""monitoring_service.py — mon_* 테이블 저장 서비스

Leader Agent 파이프라인의 각 Step 완료 시점에 호출된다.
모든 public 메서드는 try/except 없이 예외를 그대로 올린다 — 호출부(leader.py)가 try/except로 감싼다.

Gate Rule (MVP):
  Gate 1 (WARNING): Concept confidence < 0.7
  Gate 2 (BLOCK)  : 선택된 Agent 0개
  Gate 3 (WARNING): 최종 답변 문장 중 근거 없는 문장 존재
"""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.models.monitor_model import (
    MonAgentTrace,
    MonAnswerSentence,
    MonConceptDetection,
    MonGateCheck,
    MonIntentAnalysis,
    MonRoutingDecision,
    MonToolExecution,
)

# ── Gate 임계값 ────────────────────────────────────────────────────────────
_GATE1_THRESHOLD = 0.7

# concept_id 접미사 → concept_type 매핑 (순서 중요 — 긴 것 먼저)
_CONCEPT_TYPE_MAP: list[tuple[str, str]] = [
    ("PERSONAL_CREDIT_LOAN", "loan_product"),
    ("LOAN_PRODUCT",         "loan_product"),
    ("PREFERENTIAL_RATE",    "rate"),
    ("INTEREST_RATE",        "rate"),
    ("REQUIRED_DOCUMENT",    "policy"),
    ("APPLICATION_CONDITION","application"),
    ("COUNSELING_HISTORY",   "counseling"),
    ("POLICY",               "policy"),
    ("TERMS",                "policy"),
    ("CUSTOMER",             "customer"),
]


def _derive_concept_type(concept_id: str) -> str:
    for key, ctype in _CONCEPT_TYPE_MAP:
        if key in concept_id:
            return ctype
    return "unknown"


def _concept_label(concept_id: str) -> str:
    """CONCEPT_INTEREST_RATE → Interest Rate (사람이 읽는 레이블)"""
    return concept_id.replace("CONCEPT_", "").replace("_", " ").title()


# ── Tool 출력 요약 ─────────────────────────────────────────────────────────

def _summarize_tool_output(api_id: str, data: dict | None) -> str:
    """Tool 응답 데이터에서 모니터링 UI 표시용 1줄 요약 생성."""
    if not data or not isinstance(data, dict):
        return "데이터 없음"

    if api_id == "MOCK_RATE_LOOKUP":
        rates = data.get("rates", [])
        if rates:
            r = rates[0]
            return (
                f"{r.get('product_name','')}: "
                f"{r.get('min_final_rate','')}% ~ {r.get('max_final_rate','')}%"
            )

    if api_id == "MOCK_RATE_SIMULATION":
        monthly = data.get("monthly_payment", 0)
        rate    = data.get("annual_rate", 0)
        return f"월납입금 {monthly:,}원 (연 {rate}%)" if monthly else "시뮬레이션 결과 없음"

    if api_id == "MOCK_POLICY_LOOKUP":
        policies = data.get("policies", data.get("documents", []))
        if policies:
            names = [p.get("title", p.get("name", "")) for p in policies[:3]]
            return f"정책 {len(policies)}건: {', '.join(filter(None, names))}"

    if api_id == "MOCK_DOCUMENT_SEARCH":
        docs = data.get("documents", [])
        if docs:
            names = [d.get("name", "") for d in docs[:3]]
            return f"필요서류 {len(docs)}건: {', '.join(filter(None, names))}"

    if api_id == "MOCK_PRODUCT_LOOKUP":
        products = data.get("products", [])
        if products:
            p = products[0]
            return f"{p.get('name','')}: {p.get('min_rate','')}% ~ {p.get('max_rate','')}%"

    if api_id == "MOCK_ELIGIBILITY_CHECK":
        eligible = data.get("eligible", False)
        rec      = data.get("recommendation", "")
        status   = "신청 가능" if eligible else "신청 조건 미충족"
        return f"{status} — {rec[:60]}" if rec else status

    if api_id == "MOCK_EXCHANGE_RATE_LOOKUP":
        rates = data.get("rates", [])
        if rates:
            r = rates[0]
            return f"{r.get('currency','')}: {r.get('standard','')}원"

    if api_id == "MOCK_CURRENCY_EXCHANGE_CALC":
        return (
            f"{data.get('from_amount','')} {data.get('from_currency','')} → "
            f"{data.get('to_amount','')} {data.get('to_currency','')}"
        )

    if api_id == "MOCK_FOREIGN_REMITTANCE":
        daily = data.get("daily_limit_usd") or 0
        fee   = data.get("fee_estimate_krw")
        fee_str = f"{fee:,}원" if fee is not None else "미정"
        return f"1일 한도 ${daily:,} / 예상 수수료 {fee_str}"

    if api_id == "MOCK_FOREIGN_DEPOSIT_RATE":
        deposit_rates = data.get("deposit_rates", [])
        if deposit_rates:
            r = deposit_rates[0]
            return f"{r.get('currency','')} 정기 12개월 {r.get('time_deposit_12m','')}%"

    if api_id in ("MOCK_NOTIFICATION_RULES", "MOCK_NOTIFICATION_SEND"):
        return f"{api_id} 결과: {len(data)}개 필드"

    # Generic fallback
    keys = list(data.keys())[:3]
    return f"{', '.join(keys)} 등 {len(data)}개 필드"


# ── 문장 근거 검사 ─────────────────────────────────────────────────────────

# 금융 수치 패턴: 숫자 + 금융 단위 (%, 원, 개월, $, USD 등)
_NUM_PATTERN = re.compile(
    r'\d[\d,]*(?:\.\d+)?(?:\s*(?:%|원|개월|년|만|억|달러|\$|USD|KRW|EUR|JPY))',
    re.IGNORECASE,
)


def _extract_numbers(text: str) -> list[str]:
    """텍스트에서 금융 수치 패턴 추출."""
    return _NUM_PATTERN.findall(text)


def _check_grounding(
    sentence: str,
    tool_output_map: dict[str, dict],   # api_id → {agent: str, data_text: str, summary: str}
) -> tuple[bool, str | None, str | None, str | None]:
    """
    문장이 tool output에 근거하는지 확인한다.

    Returns:
        (grounded, source_agent, source_tool, evidence_summary)
    """
    numbers = _extract_numbers(sentence)

    if not numbers:
        # 숫자 없는 문장 (안내·절차 문장) → 보수적으로 grounded=True
        return True, None, None, "숫자 없는 일반 안내 문장"

    # 숫자가 있으면 각 tool output에서 해당 숫자를 검색
    # 단위(%, 원, 개월 등)를 제거한 순수 숫자 값만 비교 — tool output의 JSON에는 단위가 없음
    bare_numbers = [re.sub(r'[^0-9,.]', '', n) for n in numbers]
    bare_numbers = [n.replace(",", "") for n in bare_numbers if len(n) >= 2]  # 단일 자리 숫자 제외 (오탐 방지)

    for api_id, info in tool_output_map.items():
        data_text = info.get("data_text", "").replace(",", "")
        if any(bare in data_text for bare in bare_numbers):
            return True, info.get("agent"), api_id, info.get("summary")

    # 숫자가 있지만 tool output 어디에도 없음 → Hallucination 가능성
    return False, None, None, None


def _split_sentences(text: str) -> list[str]:
    """답변 텍스트를 문장 단위로 분리. '■' 헤더, 줄바꿈, '·' 항목 기준."""
    # 줄 단위로 먼저 분리
    lines = [line.strip() for line in text.splitlines()]
    sentences: list[str] = []
    for line in lines:
        if not line:
            continue
        # '·' 으로 시작하는 항목은 개별 문장으로 처리
        if line.startswith("·"):
            sentences.append(line)
        elif line.startswith("■"):
            sentences.append(line)
        else:
            # 마침표 기준으로 추가 분리
            parts = [p.strip() for p in re.split(r'(?<=[.。])\s+', line) if p.strip()]
            sentences.extend(parts if parts else [line])
    return [s for s in sentences if len(s) > 5]  # 너무 짧은 단편 제외


# ═══════════════════════════════════════════════════════════════════════════
# MonitoringService
# ═══════════════════════════════════════════════════════════════════════════

class MonitoringService:
    """Leader Agent 파이프라인 각 Step의 mon_* 테이블 저장 서비스."""

    # ── Step 0: 요청 헤더 생성 ─────────────────────────────────────────────

    @staticmethod
    def create_trace(
        db: Session,
        request_id: str,
        user_id: str | None,
        session_id: str | None,
        original_query: str,
    ) -> None:
        """요청 시작 시 MonAgentTrace 헤더 레코드를 생성한다 (status='processing')."""
        db.add(MonAgentTrace(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            original_query=original_query,
            status="processing",
        ))
        db.commit()

    # ── Step 1: Concept 탐지 + Gate 1 ─────────────────────────────────────

    @staticmethod
    def save_concept_detections_and_gate1(
        db: Session,
        request_id: str,
        concept_trace_rows: list[dict],
    ) -> bool:
        """
        Concept 탐지 결과를 저장하고 Gate 1을 체크한다.

        concept_trace_rows 구조 (leader.py 기준):
            {"concept_id": str, "detection_stage": str, "confidence": float,
             "source_type": str, "source_terms": list, "reason": str}

        Returns:
            True if Gate 1 WARNING triggered (confidence < 0.7 인 Concept 존재)
        """
        low_conf_concepts: list[str] = []

        for row in concept_trace_rows:
            concept_id = row.get("concept_id", "")
            confidence = float(row.get("confidence") or 0.0)
            source_terms: list = row.get("source_terms") or []
            status = "low_confidence" if confidence < _GATE1_THRESHOLD else "normal"

            if status == "low_confidence":
                low_conf_concepts.append(concept_id)

            db.add(MonConceptDetection(
                request_id=request_id,
                source_text=source_terms[0] if source_terms else None,
                concept_id=concept_id,
                concept_label=_concept_label(concept_id),
                concept_type=_derive_concept_type(concept_id),
                confidence=confidence,
                expanded_terms=source_terms,
                status=status,
            ))

        # Gate 1 체크
        if low_conf_concepts:
            msgs = [
                f"WARNING: {cid} confidence {c:.2f} < {_GATE1_THRESHOLD}"
                for cid, c in [
                    (row["concept_id"], float(row.get("confidence") or 0.0))
                    for row in concept_trace_rows
                    if float(row.get("confidence") or 0.0) < _GATE1_THRESHOLD
                ]
            ]
            db.add(MonGateCheck(
                request_id=request_id,
                gate_name="concept_confidence",
                gate_type="WARNING",
                condition=f"confidence < {_GATE1_THRESHOLD}",
                result="WARNING",
                severity="warning",
                message=" | ".join(msgs),
            ))
        else:
            db.add(MonGateCheck(
                request_id=request_id,
                gate_name="concept_confidence",
                gate_type="WARNING",
                condition=f"confidence < {_GATE1_THRESHOLD}",
                result="PASS",
                severity="info",
                message=None,
            ))

        db.commit()
        return bool(low_conf_concepts)

    # ── Step 2: Agent 라우팅 + Gate 2 ──────────────────────────────────────

    @staticmethod
    def save_routing_decisions_and_gate2(
        db: Session,
        request_id: str,
        agent_selection_rows: list[dict],
        routed_agents: list[str],
    ) -> bool:
        """
        Agent 라우팅 결정을 저장하고 Gate 2를 체크한다.

        agent_selection_rows 구조 (leader.py 기준):
            {"agent_id": str, "selected": bool, "score": float,
             "matched_concepts": list, "reason": str, "rejection_reason": str | None}

        Returns:
            True if Gate 2 BLOCKED (routed_agents가 비어 있음)
        """
        for i, row in enumerate(agent_selection_rows):
            agent_id   = row["agent_id"]
            is_selected = row["selected"]
            matched    = row.get("matched_concepts") or []
            reason     = row.get("reason") if is_selected else row.get("rejection_reason")
            score      = float(row.get("score") or 0.0)

            # score는 matched concept 수이므로 0~1로 정규화 (최대 3 assumed)
            routing_conf = min(score / max(len(matched), 1), 1.0) if matched else 0.0

            # 실행 순서: selected=True인 것 중에서 routed_agents 리스트 순서
            execution_order: int | None = None
            if is_selected and agent_id in routed_agents:
                execution_order = routed_agents.index(agent_id) + 1

            db.add(MonRoutingDecision(
                request_id=request_id,
                agent_name=agent_id,
                selected=is_selected,
                related_concepts=matched,
                reason=reason,
                routing_confidence=routing_conf,
                execution_order=execution_order,
                status="selected" if is_selected else "excluded",
            ))

        # Gate 2 체크
        blocked = len(routed_agents) == 0
        db.add(MonGateCheck(
            request_id=request_id,
            gate_name="agent_routing",
            gate_type="BLOCK",
            condition="selected_agents.length == 0",
            result="BLOCKED" if blocked else "PASS",
            severity="critical",
            message=(
                "BLOCKED: 선택된 Agent가 없습니다. "
                "Concept-Agent 매핑 또는 Intent 분석 결과를 확인해야 합니다."
                if blocked else None
            ),
        ))

        db.commit()
        return blocked

    # ── Step 3: Tool 실행 로그 ─────────────────────────────────────────────

    @staticmethod
    def save_tool_execution(
        db: Session,
        request_id: str,
        agent_name: str,
        tool_name: str,
        tool_input: dict | None,
        output_summary: str | None,
        status: str,
        latency_ms: int | None,
        retry_count: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Tool 실행 1건을 MonToolExecution에 저장한다."""
        db.add(MonToolExecution(
            request_id=request_id,
            agent_name=agent_name,
            tool_name=tool_name,
            tool_input=tool_input,
            output_summary=output_summary,
            status=status,
            latency_ms=latency_ms,
            retry_count=retry_count,
            error_message=str(error_message)[:500] if error_message else None,
        ))
        db.commit()

    # ── Step 4: 의미분석 저장 ──────────────────────────────────────────────

    @staticmethod
    def save_intent_analysis(
        db: Session,
        request_id: str,
        intent_data: dict,
        detected_concepts: list[str],
        all_concepts: list[str],
        routed_agents: list[str],
    ) -> None:
        """
        의도 분석 결과를 MonIntentAnalysis에 저장한다.
        Tool 실행 완료 후 호출해 needs_tool_execution을 정확히 기록한다.
        """
        primary_intent = intent_data.get("intent")
        keywords: list[str] = intent_data.get("keywords", [])

        # secondary_intents: 탐지된 concept 목록에서 파생
        concept_to_intent = {
            "INTEREST_RATE":        "interest_rate_lookup",
            "PREFERENTIAL_RATE":    "preferential_rate_lookup",
            "LOAN_PRODUCT":         "product_lookup",
            "PERSONAL_CREDIT_LOAN": "loan_information_lookup",
            "REQUIRED_DOCUMENT":    "required_document_lookup",
            "POLICY":               "policy_lookup",
            "TERMS":                "terms_lookup",
            "COUNSELING_HISTORY":   "counseling_history_lookup",
            "APPLICATION_CONDITION":"application_condition_lookup",
        }
        secondary: list[str] = []
        seen_sec: set[str] = set()
        for cid in detected_concepts:
            for key, intent_label in concept_to_intent.items():
                if key in cid and intent_label not in seen_sec:
                    secondary.append(intent_label)
                    seen_sec.add(intent_label)

        query_type = "multi_topic" if len(detected_concepts) > 1 else "single_topic"

        db.add(MonIntentAnalysis(
            request_id=request_id,
            primary_intent=primary_intent,
            secondary_intents=secondary,
            query_type=query_type,
            needs_tool_execution=len(routed_agents) > 0,
            needs_memory=False,
            confidence=intent_data.get("confidence"),
            reason=intent_data.get("reason") or (
                f"키워드 기반 탐지: {', '.join(keywords[:5])}" if keywords else None
            ),
        ))
        db.commit()

    # ── Step 5: 최종 답변 근거 + Gate 3 ───────────────────────────────────

    @staticmethod
    def save_answer_sentences_and_gate3(
        db: Session,
        request_id: str,
        answer: str,
        raw_results: list,                  # list[StepResult]
        tool_agent_map: dict[str, str] | None = None,  # api_id → agent_id
    ) -> bool:
        """
        최종 답변을 문장 단위로 분리해 근거를 추적하고 Gate 3를 체크한다.

        Returns:
            True if Gate 3 WARNING triggered (grounded=False 문장 존재)
        """
        # tool output 맵 빌드: api_id → {agent, data_text, summary}
        tool_output_map: dict[str, dict] = {}
        for result in raw_results:
            if result.status == "success" and result.data:
                api_id = result.api_id
                agent  = (tool_agent_map or {}).get(api_id, "")
                tool_output_map[api_id] = {
                    "agent":     agent,
                    "data_text": json.dumps(result.data, ensure_ascii=False),
                    "summary":   _summarize_tool_output(api_id, result.data),
                }

        sentences = _split_sentences(answer)
        has_ungrounded = False

        for sentence in sentences:
            grounded, src_agent, src_tool, ev_summary = _check_grounding(
                sentence, tool_output_map
            )
            if not grounded:
                has_ungrounded = True

            db.add(MonAnswerSentence(
                request_id=request_id,
                answer_sentence=sentence[:1000],
                source_agent=src_agent,
                source_tool=src_tool,
                evidence_summary=ev_summary,
                grounded=grounded,
                warning_message=(
                    "Tool 결과에 없는 수치가 포함됨. Hallucination 가능성. 검토 필요."
                    if not grounded else None
                ),
            ))

        # Gate 3 체크
        db.add(MonGateCheck(
            request_id=request_id,
            gate_name="answer_grounding",
            gate_type="WARNING",
            condition="grounded == false",
            result="WARNING" if has_ungrounded else "PASS",
            severity="warning" if has_ungrounded else "info",
            message=(
                "WARNING: 최종 답변 중 근거와 연결되지 않은 문장이 있습니다. "
                "Hallucination 가능성이 있으므로 검토가 필요합니다."
                if has_ungrounded else None
            ),
        ))

        db.commit()
        return has_ungrounded

    # ── Step 6: 트레이스 상태 최종 업데이트 ───────────────────────────────

    @staticmethod
    def finalize_trace(
        db: Session,
        request_id: str,
        status: str,
        total_latency_ms: int,
        normalized_query: str | None = None,
    ) -> None:
        """MonAgentTrace의 status와 latency를 최종 업데이트한다."""
        update_vals: dict = {
            "status": status,
            "total_latency_ms": total_latency_ms,
        }
        if normalized_query:
            update_vals["normalized_query"] = normalized_query[:500]

        db.query(MonAgentTrace).filter(
            MonAgentTrace.request_id == request_id
        ).update(update_vals)
        db.commit()

    # ── 유틸리티 ──────────────────────────────────────────────────────────

    @staticmethod
    def summarize_output(api_id: str, data: dict | None) -> str | None:
        """Tool 출력 데이터 요약 — leader.py 인라인 호출용."""
        return _summarize_tool_output(api_id, data)
