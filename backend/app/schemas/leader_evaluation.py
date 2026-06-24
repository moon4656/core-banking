from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    intent_score: float | None
    concept_score: float | None
    routing_score: float | None
    tool_success_score: float | None
    evidence_score: float | None
    final_score: float | None


class LeaderEvaluationListItemResponse(BaseModel):
    request_id: str
    user_question: str | None
    detected_intent: str | None
    intent_match_yn: bool | None
    detected_concepts: list[str]
    direct_concepts: list[str]
    expanded_concepts: list[str]
    unrouted_concepts: list[str]
    selected_agents: list[str]
    leader_confidence_score: float | None
    avg_evidence_confidence: float | None
    avg_data_quality_score: float | None
    avg_intent_relevance_score: float | None
    hallucination_yn: bool | None
    overall_result: str | None
    review_reason: str | None
    score_breakdown: ScoreBreakdown | None
    reviewer: str | None
    reviewed_at: str | None
    tool_success_count: int
    tool_failed_count: int
    created_at: str | None


class LeaderEvaluationListResponse(BaseModel):
    items: list[LeaderEvaluationListItemResponse]
    total: int


class LeaderDecisionResponse(BaseModel):
    detected_intent: str | None
    expected_intent: str | None
    intent_match_yn: bool | None
    detected_concepts: list[str]
    direct_concepts: list[str]
    expanded_concepts: list[str]
    unrouted_concepts: list[str]
    expected_concepts: list[str]
    missing_concepts: list[str]
    extra_concepts: list[str]
    selected_agents: list[str]
    expected_agents: list[str]
    missing_agents: list[str]
    extra_agents: list[str]
    step_count: int
    successful_step_count: int
    failed_step_count: int
    leader_confidence_score: float | None
    intent_keywords: list[str]
    intent_urgency: str | None
    memory_turns: int
    ltm_turns: int
    review_reason: str | None
    score_breakdown: ScoreBreakdown | None


class EvidenceSummaryResponse(BaseModel):
    evidence_count: int
    avg_evidence_confidence: float | None
    avg_data_quality_score: float | None
    avg_intent_relevance_score: float | None
    missing_concepts: list[str]
    grounding_score: float | None
    review_flags: list[str]


class LeaderEvaluationReviewResponse(BaseModel):
    final_answer_review: str | None
    hallucination_yn: bool | None
    overall_result: str | None
    review_comment: str | None
    reviewer: str | None
    reviewed_at: str | None


class LeaderEvaluationTraceEventResponse(BaseModel):
    id: int
    event_type: str
    agent_id: str | None
    tool_id: str | None
    status: str
    input_data: dict | None
    output_data: dict | None
    duration_ms: int | None
    created_at: str


class LeaderEvaluationEvidenceResponse(BaseModel):
    id: int
    concept_id: str | None
    source_id: str | None
    agent_id: str | None
    confidence_score: float | None
    data_quality_score: float | None
    intent_relevance_score: float | None
    response_latency_ms: int | None
    item_count: int | None
    quality_flags: dict | None
    related_evidence_ids: list[int] | None
    content_preview: dict | None
    created_at: str


class LeaderEvaluationDetailResponse(BaseModel):
    request_id: str
    user_question: str | None
    answer: str | None
    leader_decision: LeaderDecisionResponse
    evidence_summary: EvidenceSummaryResponse
    review: LeaderEvaluationReviewResponse
    trace_events: list[LeaderEvaluationTraceEventResponse]
    evidences: list[LeaderEvaluationEvidenceResponse]
