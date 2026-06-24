import { getStoredSession } from "@/lib/session";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:18000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export type AuthSessionResponse = {
  name: string;
  role: "READONLY" | "ANALYST" | "ADMIN";
  auth_mode: string;
  access_token: string;
  token_type: string;
};

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = getStoredSession();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(session?.accessToken
        ? { Authorization: `${session.tokenType} ${session.accessToken}` }
        : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `${response.status} request failed`;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Ignore JSON parsing errors and keep fallback detail.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

export function apiGet<T>(path: string) {
  return request<T>(path);
}

export function apiPost<T>(path: string, body: unknown) {
  return request<T>(path, { method: "POST", body });
}

export function apiPut<T>(path: string, body: unknown) {
  return request<T>(path, { method: "PUT", body });
}

export function apiDelete<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}

// ─── Decision Graph ──────────────────────────────────────────

export type DecisionListItem = {
  request_id: string;
  query_preview: string | null;
  intent: string | null;
  selected_agents: string[];
  node_count: number;
  edge_count: number;
  tool_count: number;
  review_status: string;
  created_at: string;
};

export type DecisionListResponse = {
  items: DecisionListItem[];
  total: number;
  page: number;
  size: number;
};

export type GraphNode = {
  id: string;
  node_type: string;
  label: string;
  status: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
  duration_ms: number | null;
};

export type GraphEdge = {
  id: string;
  edge_type: string;
  source: string;
  target: string;
  label: string | null;
  data: Record<string, unknown>;
  weight: number;
};

export type DecisionGraphResponse = {
  request_id: string;
  created_at: string | null;
  summary: {
    intent: string | null;
    selected_agents: string[];
    node_count: number;
    edge_count: number;
    tool_count: number;
    concept_count: number;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
  review: {
    status: string;
    reviewer_id: string | null;
    overall_result: string | null;
    intent_correct: boolean | null;
    concept_complete: boolean | null;
    agent_correct: boolean | null;
    evidence_sufficient: boolean | null;
    answer_appropriate: boolean | null;
    missing_concepts: string[];
    wrong_agents: string[];
    comment: string | null;
    review_score: number | null;
    reviewed_at: string | null;
  };
};

export type DecisionMemoryBucket = {
  loaded: boolean;
  summary: string | null;
  items_count: number;
  impact: string[];
  items: Array<{
    role?: string | null;
    content?: string | null;
    question?: string | null;
    answer?: string | null;
    intent?: string | null;
    concepts?: string[];
    keywords?: string[];
  }>;
};

export type DecisionIntentAnalysis = {
  intent: string | null;
  confidence: number | null;
  keywords: string[];
  urgency: string | null;
  reason: string | null;
};

export type DecisionConceptTrace = {
  concept_id: string;
  detection_stage: string;
  confidence: number | null;
  source_type: string | null;
  source_terms: string[];
  reason: string | null;
};

export type DecisionAgentSelectionItem = {
  agent_name: string;
  selected: boolean;
  score: number | null;
  matched_concepts: string[];
  reason: string;
  rejection_reason: string | null;
};

export type DecisionToolExecution = {
  tool_name: string;
  agent_name: string;
  concept_ids: string[];
  input_summary: string | null;
  output_summary: string | null;
  status: string;
  latency_ms: number | null;
  evidence_ids: number[];
};

export type DecisionTraceResponse = {
  request_id: string;
  user_query: string;
  normalized_query: string | null;
  memory: {
    short_memory: DecisionMemoryBucket;
    long_term_memory: DecisionMemoryBucket;
  };
  intent_analysis: DecisionIntentAnalysis;
  concepts: DecisionConceptTrace[];
  leader_decision: {
    description: string | null;
    selected_agents: string[];
    rejected_agents: string[];
    direct_concepts: string[];
    expanded_concepts: string[];
    unrouted_concepts: string[];
    confidence: number | null;
    total_steps: number | null;
    reason: string | null;
  };
  agent_selection: {
    selected_agents: DecisionAgentSelectionItem[];
    rejected_agents: DecisionAgentSelectionItem[];
  };
  tool_executions: DecisionToolExecution[];
  reranking: {
    criteria_weights: Record<string, number>;
    candidates: Array<Record<string, unknown>>;
    selected_evidence_ids: number[];
    reason: string | null;
  };
  final_answer: {
    answer: string;
    answer_summary: string | null;
    used_evidence_ids: number[];
    grounding_summary: string | null;
  };
  latency: {
    total_ms?: number;
    steps?: Array<{ step: string; latency_ms: number }>;
    agent_steps?: Array<{ agent_name: string; latency_ms: number }>;
  };
};

export function fetchDecisions(page = 1, size = 20, intent?: string) {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (intent) params.set("intent", intent);
  return apiGet<DecisionListResponse>(`/api/v1/ai/decisions?${params}`);
}

export function fetchDecisionGraph(requestId: string) {
  return apiGet<DecisionGraphResponse>(`/api/v1/ai/decisions/${requestId}/graph`);
}

export function fetchDecisionTrace(requestId: string) {
  return apiGet<DecisionTraceResponse>(`/api/v1/ai/decisions/${requestId}/trace`);
}

export function saveDecisionReview(requestId: string, body: Record<string, unknown>) {
  return apiPost<{ saved: boolean; status: string }>(
    `/api/v1/ai/decisions/${requestId}/review`,
    body,
  );
}

// ─── Monitoring ──────────────────────────────────────────────

export type MonitoringSummary = {
  total_requests: number;
  completed_count: number;
  success_rate: number;
  avg_latency_ms: number;
  error_count: number;
};

export type AgentStat = {
  agent_id: string;
  call_count: number;
  success_rate: number;
  avg_latency_ms: number;
};

export type ToolStat = {
  tool_id: string;
  call_count: number;
  success_rate: number;
  avg_latency_ms: number;
};

export type PipelineLatencyItem = {
  event_type: string;
  label: string;
  avg_ms: number;
  count: number;
};

export type RecentError = {
  request_id: string;
  event_type: string;
  agent_id: string | null;
  tool_id: string | null;
  output_data: Record<string, unknown> | null;
  ts: string | null;
};

export type MonitoringMetrics = {
  period_hours: number;
  summary: MonitoringSummary;
  intent_distribution: Record<string, number>;
  agent_stats: AgentStat[];
  tool_stats: ToolStat[];
  pipeline_latency: PipelineLatencyItem[];
  recent_errors: RecentError[];
};

export type PipelineEvent = {
  id: number;
  event_type: string;
  label: string;
  agent_id: string | null;
  tool_id: string | null;
  status: string;
  duration_ms: number | null;
  output_data: Record<string, unknown> | null;
  ts: string | null;
};

export function fetchMonitoringMetrics(hours = 24) {
  return apiGet<MonitoringMetrics>(`/api/v1/monitoring/metrics?hours=${hours}`);
}

export function fetchLatestRequestId() {
  return apiGet<{ request_id: string | null; created_at: string | null }>(
    "/api/v1/monitoring/latest",
  );
}

export function getMonitoringStreamUrl(requestId: string): string {
  return `${API_BASE_URL}/api/v1/monitoring/stream/${requestId}`;
}

// ─── Leader Agent Pipeline Monitor ───────────────────────────

export type MonTraceListItem = {
  request_id: string;
  user_id: string | null;
  session_id: string | null;
  original_query: string | null;
  status: string;                  // completed | warning | blocked | processing
  total_latency_ms: number | null;
  created_at: string;
};

export type MonTraceListResponse = {
  items: MonTraceListItem[];
  total: number;
  page: number;
  size: number;
};

export type MonGateDetail = {
  gate_name: string | null;
  gate_type: string | null;
  condition: string | null;
  result: string | null;           // PASS | WARNING | BLOCKED
  severity: string | null;
  message: string | null;
};

export type MonIntentDetail = {
  primary_intent: string | null;
  secondary_intents: string[];
  query_type: string | null;
  needs_tool_execution: boolean;
  needs_memory: boolean;
  confidence: number | null;
  reason: string | null;
};

export type MonConceptDetail = {
  concept_id: string | null;
  concept_label: string | null;
  concept_type: string | null;
  source_text: string | null;
  confidence: number | null;
  expanded_terms: string[];
  status: string | null;
};

export type MonRoutingDetail = {
  agent_name: string | null;
  selected: boolean;
  related_concepts: string[];
  reason: string | null;
  routing_confidence: number | null;
  execution_order: number | null;
  status: string | null;           // selected | excluded
};

export type MonToolDetail = {
  agent_name: string | null;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  output_summary: string | null;
  status: string | null;
  latency_ms: number | null;
  retry_count: number;
  error_message: string | null;
};

export type MonSentenceDetail = {
  answer_sentence: string | null;
  source_agent: string | null;
  source_tool: string | null;
  evidence_summary: string | null;
  grounded: boolean;
  warning_message: string | null;
};

export type MonTraceDetailResponse = {
  trace: MonTraceListItem;
  intent: MonIntentDetail | null;
  concepts: MonConceptDetail[];
  routing: MonRoutingDetail[];
  tools: MonToolDetail[];
  sentences: MonSentenceDetail[];
  gates: MonGateDetail[];
};

export function fetchMonTraces(page = 1, size = 20, status?: string) {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (status) params.set("status", status);
  return apiGet<MonTraceListResponse>(`/api/v1/leader-agent/traces?${params}`);
}

export function fetchMonTraceDetail(requestId: string) {
  return apiGet<MonTraceDetailResponse>(`/api/v1/leader-agent/traces/${requestId}`);
}

// ─────────────────────────────────────────────────────────────

export async function authLogin(name: string, apiKey: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({
      name,
      apiKey,
    }),
  });

  if (!response.ok) {
    let detail = "login failed";
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Ignore parsing failure.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<AuthSessionResponse>;
}
