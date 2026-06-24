export type TraceSummary = {
  request_id: string;
  owner_name: string | null;
  owner_role: string | null;
  event_count: number;
  evidence_count: number;
  avg_confidence: number | null;
  avg_data_quality: number | null;
  avg_intent_relevance: number | null;
  linked_evidence_count: number;
  events_by_type: Record<string, number>;
};

export type TraceListItem = {
  request_id: string;
  owner_name: string | null;
  owner_role: string | null;
  first_event_at: string;
  last_event_at: string;
  event_count: number;
  evidence_count: number;
  last_event_type: string;
  query_preview: string | null;
  intent: string | null;
  selected_agents_count: number;
  concept_count: number;
};

export type TraceOwnerUpdateResponse = {
  request_id: string;
  owner_name: string;
  owner_role: string | null;
};

export type TraceEvent = {
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

export type EvidenceItem = {
  id: number;
  concept_id: string | null;
  source_id: string | null;
  confidence_score: number | null;
  data_quality_score: number | null;
  intent_relevance_score: number | null;
  response_latency_ms: number | null;
  item_count: number | null;
  quality_flags: Record<string, unknown> | null;
  related_evidence_ids: number[] | null;
  created_at: string;
};
