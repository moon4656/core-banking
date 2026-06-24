export type ScoreBreakdown = {
  intent_score: number | null;
  concept_score: number | null;
  routing_score: number | null;
  tool_success_score: number | null;
  evidence_score: number | null;
  final_score: number | null;
};

export type LeaderEvaluationListItem = {
  request_id: string;
  user_question: string | null;
  detected_intent: string | null;
  intent_match_yn: boolean | null;
  detected_concepts: string[];
  direct_concepts: string[];
  expanded_concepts: string[];
  unrouted_concepts: string[];
  selected_agents: string[];
  leader_confidence_score: number | null;
  avg_evidence_confidence: number | null;
  avg_data_quality_score: number | null;
  avg_intent_relevance_score: number | null;
  hallucination_yn: boolean | null;
  overall_result: string | null;
  review_reason: string | null;
  score_breakdown: ScoreBreakdown | null;
  reviewer: string | null;
  reviewed_at: string | null;
  tool_success_count: number;
  tool_failed_count: number;
  created_at: string | null;
};

export type LeaderEvaluationListResponse = {
  items: LeaderEvaluationListItem[];
  total: number;
};

export type LeaderDecisionDetail = {
  detected_intent: string | null;
  expected_intent: string | null;
  intent_match_yn: boolean | null;
  detected_concepts: string[];
  direct_concepts: string[];
  expanded_concepts: string[];
  unrouted_concepts: string[];
  expected_concepts: string[];
  missing_concepts: string[];
  extra_concepts: string[];
  selected_agents: string[];
  expected_agents: string[];
  missing_agents: string[];
  extra_agents: string[];
  step_count: number;
  successful_step_count: number;
  failed_step_count: number;
  leader_confidence_score: number | null;
  intent_keywords: string[];
  intent_urgency: string | null;
  memory_turns: number;
  ltm_turns: number;
  review_reason: string | null;
  score_breakdown: ScoreBreakdown | null;
};

export type LeaderEvaluationEvidenceSummary = {
  evidence_count: number;
  avg_evidence_confidence: number | null;
  avg_data_quality_score: number | null;
  avg_intent_relevance_score: number | null;
  missing_concepts: string[];
  grounding_score: number | null;
  review_flags: string[];
};

export type LeaderEvaluationReview = {
  final_answer_review: string | null;
  hallucination_yn: boolean | null;
  overall_result: string | null;
  review_comment: string | null;
  reviewer: string | null;
  reviewed_at: string | null;
};

export type LeaderEvaluationTraceEvent = {
  id: number;
  event_type: string;
  agent_id: string | null;
  tool_id: string | null;
  status: string;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  duration_ms: number | null;
  created_at: string;
};

export type LeaderEvaluationEvidence = {
  id: number;
  concept_id: string | null;
  source_id: string | null;
  agent_id: string | null;
  confidence_score: number | null;
  data_quality_score: number | null;
  intent_relevance_score: number | null;
  response_latency_ms: number | null;
  item_count: number | null;
  quality_flags: Record<string, unknown> | null;
  related_evidence_ids: number[] | null;
  content_preview: Record<string, unknown> | null;
  created_at: string;
};

export type LeaderEvaluationDetail = {
  request_id: string;
  user_question: string | null;
  answer: string | null;
  leader_decision: LeaderDecisionDetail;
  evidence_summary: LeaderEvaluationEvidenceSummary;
  review: LeaderEvaluationReview;
  trace_events: LeaderEvaluationTraceEvent[];
  evidences: LeaderEvaluationEvidence[];
};
