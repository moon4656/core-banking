export type ExecutionStep = {
  step_index: number;
  agent_id: string;
  concept_id: string;
  api_id: string;
  params: Record<string, unknown>;
};

export type ExecutionPlan = {
  request_id: string;
  message: string;
  detected_concepts: string[];
  routed_agents: string[];
  steps: ExecutionStep[];
};

export type StepResult = {
  step_index: number;
  api_id: string;
  status: string;
  data: Record<string, unknown> | unknown[] | null;
  error: string | null;
};

export type ChatResponse = {
  request_id: string;
  message: string;
  plan: ExecutionPlan;
  results: StepResult[];
  answer: string;
  intent: Record<string, unknown>;
  memory_turns: number;
  trace_count: number;
  evidence_count: number;
};
