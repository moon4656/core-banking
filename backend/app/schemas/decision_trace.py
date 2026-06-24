from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    role: str | None = None
    content: str | None = None
    question: str | None = None
    answer: str | None = None
    intent: str | None = None
    concepts: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class MemoryBucket(BaseModel):
    loaded: bool
    summary: str | None = None
    items_count: int = 0
    impact: list[str] = Field(default_factory=list)
    items: list[MemoryItem] = Field(default_factory=list)


class IntentAnalysisResponse(BaseModel):
    intent: str | None
    confidence: float | None
    keywords: list[str] = Field(default_factory=list)
    urgency: str | None = None
    reason: str | None = None


class ConceptTraceResponse(BaseModel):
    concept_id: str
    detection_stage: str
    confidence: float | None
    source_type: str | None
    source_terms: list[str] = Field(default_factory=list)
    reason: str | None = None


class AgentSelectionItemResponse(BaseModel):
    agent_name: str
    selected: bool
    score: float | None
    matched_concepts: list[str] = Field(default_factory=list)
    reason: str
    rejection_reason: str | None = None


class ToolExecutionResponse(BaseModel):
    tool_name: str
    agent_name: str
    concept_ids: list[str] = Field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    status: str
    latency_ms: int | None = None
    evidence_ids: list[int] = Field(default_factory=list)


class LeaderDecisionResponse(BaseModel):
    description: str | None = None
    selected_agents: list[str] = Field(default_factory=list)
    rejected_agents: list[str] = Field(default_factory=list)
    direct_concepts: list[str] = Field(default_factory=list)
    expanded_concepts: list[str] = Field(default_factory=list)
    unrouted_concepts: list[str] = Field(default_factory=list)
    confidence: float | None = None
    total_steps: int | None = None
    reason: str | None = None


class DecisionTraceDetailResponse(BaseModel):
    request_id: str
    user_query: str
    normalized_query: str | None = None
    memory: dict[str, MemoryBucket]
    intent_analysis: IntentAnalysisResponse
    concepts: list[ConceptTraceResponse]
    leader_decision: LeaderDecisionResponse
    agent_selection: dict[str, list[AgentSelectionItemResponse]]
    tool_executions: list[ToolExecutionResponse]
    reranking: dict[str, Any]
    final_answer: dict[str, Any]
    latency: dict[str, Any]


# ═══════════════════════════════════════════════════════════════
# Decision Graph v2 스키마
# ═══════════════════════════════════════════════════════════════


class ConceptCategory(str, Enum):
    """Concept 분류 계층 — confidence threshold 기반으로 결정된다."""
    CORE       = "core"        # threshold ≥ 0.80 : 질문을 직접 해결하는 핵심 개념
    SUPPORTING = "supporting"  # threshold ≥ 0.65 : 핵심 답변을 보조/검증하는 개념
    REFERENCE  = "reference"   # threshold ≥ 0.60 : 도메인 맥락을 잡는 참고 개념


class ConceptItem(BaseModel):
    """v2 Concept 탐지 단일 항목 — category, threshold, 강등/승격 이력 포함."""
    name: str
    category: ConceptCategory
    confidence: float
    threshold: float
    reason: str | None = None
    promoted_from: ConceptCategory | None = None  # 승격 이전 카테고리
    demoted_from: ConceptCategory | None = None   # 강등 이전 카테고리


class ClassifiedConcepts(BaseModel):
    """Core / Supporting / Reference 계층으로 분류된 Concept 묶음."""
    core: list[ConceptItem] = Field(default_factory=list)
    supporting: list[ConceptItem] = Field(default_factory=list)
    reference: list[ConceptItem] = Field(default_factory=list)

    def all_concepts(self) -> list[ConceptItem]:
        return self.core + self.supporting + self.reference


class DecisionRule(BaseModel):
    """Leader가 Agent 선택에 적용한 단일 결정 규칙."""
    rule_id: str
    rule_name: str
    triggered: bool


class SelectedAgentV2(BaseModel):
    """v2 선택 Agent 항목 — role, execution_mode, Tool 목록, 선행 의존성 포함."""
    agent_name: str
    role: str                          # product_identification / rate_lookup / document_and_policy_check 등
    score: float
    reason: str
    execution_mode: str = "normal"     # lightweight | normal
    tools: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class RejectedAgentV2(BaseModel):
    """v2 미선택 Agent 항목 — 점수와 미선택 사유 포함."""
    agent_name: str
    score: float
    reason: str


class ContextLoaded(BaseModel):
    """Context Load 단계 결과 — Short/Long-term Memory 로드 요약."""
    short_memory_turns: int = 0
    long_term_summary: str | None = None
    context_applied: bool = False


class IntentV2(BaseModel):
    """v2 Intent 분석 결과 — fallback 여부 포함."""
    name: str
    confidence: float
    reason: str | None = None
    fallback_triggered: bool = False
    fallback_reason: str | None = None


class LeaderDecisionV2(BaseModel):
    """
    Leader Agent Decision 결과 v2 전체 스키마.

    Section 8의 설계 기준을 따른다.
    - concepts: Core/Supporting/Reference 3단계 분류
    - decision_rules_applied: 적용된 결정 룰 감사 로그
    - selected_agents/rejected_agents: 선택/미선택 사유 포함
    - execution_strategy: parallel | serial
    """
    request_id: str
    session_id: str | None = None
    schema_version: str = "v2.0"
    created_at: str | None = None

    user_query: str
    user_query_masked: str | None = None

    context_loaded: ContextLoaded = Field(default_factory=ContextLoaded)
    intent: IntentV2
    concepts: ClassifiedConcepts = Field(default_factory=ClassifiedConcepts)
    decision_rules_applied: list[DecisionRule] = Field(default_factory=list)

    selected_agents: list[SelectedAgentV2] = Field(default_factory=list)
    rejected_agents: list[RejectedAgentV2] = Field(default_factory=list)

    execution_strategy: str = "parallel"
    parallelization_groups: list[list[str]] = Field(default_factory=list)
    serial_prerequisite: list[str] = Field(default_factory=list)

    estimated_execution_ms: int | None = None
    decision_reason: str | None = None

    # Phase 5 — Answer Slot Ranking
    answer_slots: list["AnswerSlot"] = Field(default_factory=list)
    slot_rankings: list["AnswerSlotRanking"] = Field(default_factory=list)

    # Phase 6 — Validation
    risk_flags: list[str] = Field(default_factory=list)   # 실패한 check_id 목록
    actions_taken: list[str] = Field(default_factory=list) # 수행된 조치 목록
    requires_disclaimer: bool = False


# ═══════════════════════════════════════════════════════════════
# Phase 5 — Answer Slot Ranking 스키마
# ═══════════════════════════════════════════════════════════════


class AnswerSlot(BaseModel):
    """
    복합 질문의 단일 답변 항목(슬롯).

    "금리와 필요서류 알려줘" → interest_rate + required_document 두 슬롯 생성.
    slot_name   : concept_constants.SLOT_CONCEPT_MAP의 키와 일치
    label_ko    : 운영자 UI 표시용 한국어 레이블
    concept_ids : 이 슬롯과 연결된 Concept ID 목록
    tools       : 이 슬롯을 채울 수 있는 Tool ID 목록 (SLOT_TOOL_MAP 기반)
    """
    slot_name: str
    label_ko: str
    concept_ids: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class EvidenceCandidate(BaseModel):
    """Answer Slot 랭킹 후보 Evidence 1건."""
    evidence_id: int | None = None
    api_id: str
    confidence_score: float
    rank: int = 1


class AnswerSlotRanking(BaseModel):
    """
    Answer Slot 1개에 대한 Evidence 랭킹 결과.

    slot_filled=True  : best_evidence가 있어 답변 가능
    slot_filled=False : 관련 Evidence 없음 (해당 Tool이 실행되지 않은 경우)
    """
    slot_name: str
    label_ko: str
    best_evidence: EvidenceCandidate | None = None
    candidates: list[EvidenceCandidate] = Field(default_factory=list)
    slot_filled: bool = False
