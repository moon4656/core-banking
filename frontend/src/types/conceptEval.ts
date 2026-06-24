export type EvalQuery = {
  category: string;
  message: string;
  expected_agents: string[];
};

export type EvalResult = {
  category: string;
  message: string;
  expected_agents: string[];      // 기대 라우팅 Agent
  detected_concepts: string[];    // 탐지된 Concept (참고용)
  direct_concepts: string[];
  expanded_concepts: string[];
  routed_agents: string[];        // 실제 라우팅된 Agent
  true_positive: string[];        // 올바르게 라우팅된 Agent
  false_positive: string[];       // 불필요하게 라우팅된 Agent
  false_negative: string[];       // 누락된 Agent
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  grade: "A" | "B" | "C" | "D" | "F" | "-";
};

export type CategorySummary = {
  total: number;
  avg_f1: number | null;
  grades: Record<string, number>;
};

export type EvalSummary = {
  total: number;
  avg_f1: number | null;
  overall_grade: string;
  grade_distribution: Record<string, number>;
  by_category: Record<string, CategorySummary>;
};

export type BatchEvalResponse = {
  total: number;
  results: EvalResult[];
  summary: EvalSummary;
};

export type SaveEvalRunRequest = {
  run_type: "ALL" | "SELECTED";
  category: string | null;
  results: EvalResult[];
  summary: EvalSummary;
};

export type EvalRunSummary = {
  run_id: string;
  run_at: string;
  run_type: "ALL" | "SELECTED";
  category: string | null;
  total_queries: number;
  avg_f1: number | null;
  overall_grade: string;
};

export type EvalRunDetail = EvalRunSummary & {
  summary_json: EvalSummary | null;
  items: EvalResult[];
};

export type CustomQueryRow = EvalQuery & { id: number };
