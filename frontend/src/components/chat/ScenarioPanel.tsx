"use client";

import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import CancelRoundedIcon from "@mui/icons-material/CancelRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useState } from "react";

import {
  CATEGORY_LABEL,
  SCENARIOS,
  Scenario,
  ScenarioCategory,
} from "@/lib/scenarios";
import { ChatResponse } from "@/types/chat";

// ─────────────────────────────────────────────────────────────
// 채점 로직
// ─────────────────────────────────────────────────────────────

type DimResult = { name: string; passed: boolean; detail: string };

function scoreScenario(scenario: Scenario, response: ChatResponse): DimResult[] {
  const exp = scenario.expected;
  const results: DimResult[] = [];

  const intent = (response.intent as Record<string, string>)?.intent ?? "";
  const detected = new Set(response.plan.detected_concepts);
  const routed = new Set(response.plan.routed_agents);
  const answer = response.answer ?? "";
  const evidenceCount = response.evidence_count ?? 0;

  if (exp.intent) {
    results.push({
      name: "의도 분류",
      passed: intent === exp.intent,
      detail: `기대 ${exp.intent} / 실제 ${intent || "—"}`,
    });
  }

  for (const cid of exp.mustDetectConcepts) {
    results.push({
      name: `Concept: ${cid.replace("CONCEPT_", "")}`,
      passed: detected.has(cid),
      detail: detected.has(cid) ? "탐지됨" : "미탐지",
    });
  }

  for (const aid of exp.mustSelectAgents) {
    results.push({
      name: `Agent: ${aid.replace("_AGENT", "")}`,
      passed: routed.has(aid),
      detail: routed.has(aid) ? "선택됨" : "미선택",
    });
  }

  for (const kw of exp.answerMustContain) {
    results.push({
      name: `포함: "${kw}"`,
      passed: answer.includes(kw),
      detail: answer.includes(kw) ? "포함" : "미포함",
    });
  }

  for (const kw of exp.answerMustNotContain) {
    results.push({
      name: `금지: "${kw}"`,
      passed: !answer.includes(kw),
      detail: !answer.includes(kw) ? "안전" : "포함됨",
    });
  }

  if (exp.minEvidence > 0) {
    results.push({
      name: `Evidence ≥ ${exp.minEvidence}`,
      passed: evidenceCount >= exp.minEvidence,
      detail: `실제 ${evidenceCount}건`,
    });
  }

  return results;
}

// ─────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────

type RunResult = {
  scenarioId: string;
  dims: DimResult[];
  passed: boolean;
};

type Props = {
  runningId: string | null;
  lastResult: RunResult | null;
  onRun: (scenario: Scenario) => void;
};

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

const CATEGORIES: ScenarioCategory[] = ["intent", "concept", "agent", "answer", "edge"];

export function ScenarioPanel({ runningId, lastResult, onRun }: Props) {
  const [activeCategory, setActiveCategory] = useState<ScenarioCategory | "all">("all");

  const filtered = activeCategory === "all"
    ? SCENARIOS
    : SCENARIOS.filter((s) => s.category === activeCategory);

  return (
    <Stack spacing={1.5} sx={{ height: "100%", overflowY: "hidden", display: "flex", flexDirection: "column" }}>

      {/* 카테고리 필터 */}
      <Stack direction="row" flexWrap="wrap" gap={0.75}>
        <Chip
          label="전체"
          size="small"
          variant={activeCategory === "all" ? "filled" : "outlined"}
          onClick={() => setActiveCategory("all")}
          sx={{ fontSize: 11 }}
        />
        {CATEGORIES.map((cat) => (
          <Chip
            key={cat}
            label={CATEGORY_LABEL[cat]}
            size="small"
            variant={activeCategory === cat ? "filled" : "outlined"}
            onClick={() => setActiveCategory(cat)}
            sx={{ fontSize: 11 }}
          />
        ))}
      </Stack>

      {/* 마지막 실행 결과 요약 */}
      {lastResult && (
        <Box
          sx={{
            p: 1.25,
            borderRadius: "12px",
            backgroundColor: lastResult.passed ? "#f0fdf4" : "#fff7ed",
            border: "1px solid",
            borderColor: lastResult.passed ? "#bbf7d0" : "#fed7aa",
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.75 }}>
            {lastResult.passed
              ? <CheckCircleRoundedIcon sx={{ fontSize: 16, color: "#16a34a" }} />
              : <CancelRoundedIcon sx={{ fontSize: 16, color: "#ea580c" }} />
            }
            <Typography variant="caption" fontWeight={700} sx={{ color: lastResult.passed ? "#15803d" : "#c2410c" }}>
              {lastResult.scenarioId} — {lastResult.passed ? "전체 통과" : "일부 실패"}
            </Typography>
          </Stack>
          <Stack spacing={0.4}>
            {lastResult.dims.map((dim) => (
              <Stack key={dim.name} direction="row" alignItems="center" spacing={0.75}>
                {dim.passed
                  ? <CheckCircleRoundedIcon sx={{ fontSize: 13, color: "#22c55e", flexShrink: 0 }} />
                  : <CancelRoundedIcon sx={{ fontSize: 13, color: "#f97316", flexShrink: 0 }} />
                }
                <Typography variant="caption" sx={{ color: "#374151", lineHeight: 1.3 }}>
                  {dim.name}
                </Typography>
                <Typography variant="caption" sx={{ color: "#6b7280", ml: "auto !important", flexShrink: 0 }}>
                  {dim.detail}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </Box>
      )}

      {/* 시나리오 목록 */}
      <Box sx={{ flex: 1, overflowY: "auto", pr: 0.5 }}>
        <Stack spacing={0.75}>
          {filtered.map((scenario) => {
            const isRunning = runningId === scenario.id;
            const isThisResult = lastResult?.scenarioId === scenario.id;

            return (
              <Box
                key={scenario.id}
                sx={{
                  p: 1.25,
                  borderRadius: "12px",
                  border: "1px solid",
                  borderColor: isThisResult
                    ? (lastResult?.passed ? "#bbf7d0" : "#fed7aa")
                    : "#e5e7eb",
                  backgroundColor: isThisResult
                    ? (lastResult?.passed ? "#f0fdf4" : "#fff7ed")
                    : "#fafafa",
                  "&:hover": { borderColor: "#9ca3af", backgroundColor: "#f3f4f6" },
                  transition: "all 0.15s",
                }}
              >
                <Stack direction="row" alignItems="flex-start" spacing={1}>
                  {/* 결과 아이콘 */}
                  <Box sx={{ pt: 0.2, flexShrink: 0 }}>
                    {isRunning ? (
                      <CircularProgress size={14} />
                    ) : isThisResult ? (
                      lastResult?.passed
                        ? <CheckCircleRoundedIcon sx={{ fontSize: 16, color: "#22c55e" }} />
                        : <CancelRoundedIcon sx={{ fontSize: 16, color: "#f97316" }} />
                    ) : (
                      <Box sx={{ width: 16, height: 16 }} />
                    )}
                  </Box>

                  {/* 내용 */}
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Stack direction="row" alignItems="center" spacing={0.75} sx={{ mb: 0.5 }}>
                      <Chip label={scenario.id} size="small" sx={{ fontSize: 10, height: 18 }} />
                      <Chip
                        label={CATEGORY_LABEL[scenario.category]}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: 10, height: 18 }}
                      />
                    </Stack>
                    <Tooltip title={scenario.description} placement="left" arrow>
                      <Typography
                        variant="body2"
                        sx={{
                          lineHeight: 1.45,
                          display: "-webkit-box",
                          WebkitBoxOrient: "vertical",
                          WebkitLineClamp: 2,
                          overflow: "hidden",
                          cursor: "default",
                        }}
                      >
                        {scenario.question}
                      </Typography>
                    </Tooltip>
                    {/* 기대값 요약 */}
                    <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mt: 0.6 }}>
                      {scenario.expected.intent && (
                        <Chip label={scenario.expected.intent} size="small" variant="outlined"
                          sx={{ fontSize: 9, height: 16, color: "#6366f1", borderColor: "#c7d2fe" }} />
                      )}
                      {scenario.expected.mustSelectAgents.map((a) => (
                        <Chip key={a} label={a.replace("_AGENT", "")} size="small" variant="outlined"
                          sx={{ fontSize: 9, height: 16, color: "#0891b2", borderColor: "#bae6fd" }} />
                      ))}
                    </Stack>
                  </Box>

                  {/* 실행 버튼 */}
                  <Box
                    component="button"
                    onClick={() => !isRunning && onRun(scenario)}
                    disabled={isRunning}
                    sx={{
                      flexShrink: 0,
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      border: "none",
                      cursor: isRunning ? "default" : "pointer",
                      backgroundColor: isRunning ? "#e5e7eb" : "#111827",
                      color: "#ffffff",
                      display: "grid",
                      placeItems: "center",
                      "&:hover": { backgroundColor: isRunning ? "#e5e7eb" : "#374151" },
                      transition: "background-color 0.15s",
                    }}
                  >
                    <PlayArrowRoundedIcon sx={{ fontSize: 16 }} />
                  </Box>
                </Stack>
              </Box>
            );
          })}
        </Stack>
      </Box>

      <Divider />
      <Typography variant="caption" color="text.secondary">
        총 {SCENARIOS.length}개 시나리오 · 표시 {filtered.length}개
      </Typography>
    </Stack>
  );
}

// 외부에서 사용하는 채점 함수 재공개
export { scoreScenario };
export type { RunResult };
