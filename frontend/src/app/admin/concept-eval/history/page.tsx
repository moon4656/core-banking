"use client";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { PageCard } from "@/components/common/PageCard";
import { AppShell } from "@/components/layout/AppShell";
import { apiDelete, apiGet } from "@/lib/api";
import { EvalResult, EvalRunDetail, EvalRunSummary } from "@/types/conceptEval";

// ─────────────────────────────────────────────
// 상수
// ─────────────────────────────────────────────
const GRADE_COLOR: Record<string, "success" | "primary" | "warning" | "error" | "default"> = {
  A: "success", B: "primary", C: "warning", D: "error", F: "error", "-": "default",
};

function GradeChip({ grade }: { grade: string }) {
  return <Chip label={grade} size="small" color={GRADE_COLOR[grade] ?? "default"} sx={{ fontWeight: 700, minWidth: 32 }} />;
}

function F1Bar({ value }: { value: number | null }) {
  if (value === null) return <Typography variant="body2" color="text.secondary">-</Typography>;
  const pct = Math.round(value * 100);
  const color = value >= 0.9 ? "#2e7d32" : value >= 0.7 ? "#1565c0" : value >= 0.5 ? "#e65100" : "#c62828";
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box sx={{ width: 56, height: 6, borderRadius: 3, bgcolor: "grey.200", overflow: "hidden" }}>
        <Box sx={{ width: `${pct}%`, height: "100%", bgcolor: color, borderRadius: 3 }} />
      </Box>
      <Typography variant="body2" sx={{ minWidth: 34, color, fontWeight: 600 }}>{pct}%</Typography>
    </Box>
  );
}

// ─────────────────────────────────────────────
// 개별 실행 이력 행
// ─────────────────────────────────────────────
function RunRow({ run, onDelete }: { run: EvalRunSummary; onDelete: (id: string) => void }) {
  const detailQuery = useQuery({
    queryKey: ["concept-eval-run", run.run_id],
    queryFn: () => apiGet<EvalRunDetail>(`/api/v1/admin/concept-eval/runs/${run.run_id}`),
    enabled: false, // Accordion 열 때만 fetch
  });

  return (
    <Accordion
      onChange={(_, expanded) => {
        if (expanded && !detailQuery.data) detailQuery.refetch();
      }}
      sx={{ border: "1px solid", borderColor: "divider", borderRadius: "8px !important", mb: 1, "&:before": { display: "none" } }}
    >
      <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ px: 2 }}>
        <Stack direction="row" alignItems="center" spacing={2} sx={{ flex: 1, pr: 1 }}>
          <GradeChip grade={run.overall_grade} />
          <Typography variant="body2" sx={{ minWidth: 160, color: "text.secondary", fontSize: 12 }}>
            {new Date(run.run_at).toLocaleString("ko-KR")}
          </Typography>
          <Chip
            label={run.run_type === "ALL" ? "전체" : "선택"}
            size="small"
            color={run.run_type === "ALL" ? "default" : "primary"}
            variant="outlined"
            sx={{ fontSize: 10 }}
          />
          {run.category && (
            <Chip label={run.category} size="small" variant="outlined" sx={{ fontSize: 10 }} />
          )}
          <Typography variant="body2" color="text.secondary">{run.total_queries}건</Typography>
          <Box sx={{ flex: 1 }}>
            <F1Bar value={run.avg_f1} />
          </Box>
          <Tooltip title="이력 삭제">
            <IconButton size="small" color="error"
              onClick={(e) => { e.stopPropagation(); onDelete(run.run_id); }}>
              <DeleteOutlineRoundedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 0, borderTop: "1px solid", borderColor: "divider" }}>
        {detailQuery.isPending ? (
          <Box sx={{ display: "grid", placeItems: "center", py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : detailQuery.data ? (
          <DetailTable items={detailQuery.data.items} />
        ) : null}
      </AccordionDetails>
    </Accordion>
  );
}

function DetailTable({ items }: { items: EvalResult[] }) {
  return (
    <Box sx={{ overflowX: "auto" }}>
      <Table size="small" sx={{ minWidth: 700 }}>
        <TableHead>
          <TableRow sx={{ "& th": { fontWeight: 700, bgcolor: "grey.50", fontSize: 11 } }}>
            <TableCell sx={{ width: 100 }}>카테고리</TableCell>
            <TableCell sx={{ minWidth: 200 }}>질의</TableCell>
            <TableCell sx={{ minWidth: 160 }}>탐지 결과</TableCell>
            <TableCell sx={{ width: 70 }}>F1</TableCell>
            <TableCell sx={{ width: 50 }}>등급</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((r, i) => (
            <TableRow key={i} hover sx={{ verticalAlign: "top" }}>
              <TableCell>
                <Chip label={r.category} size="small" variant="outlined" sx={{ fontSize: 10 }} />
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontSize: 12 }}>{r.message}</Typography>
              </TableCell>
              <TableCell>
                <Stack spacing={0.4}>
                  {r.true_positive.length > 0 && (
                    <Stack direction="row" gap={0.4} flexWrap="wrap">
                      {r.true_positive.map((c) => (
                        <Chip key={c} label={c.replace("CONCEPT_", "")} size="small"
                          color="success" sx={{ fontSize: 9 }} />
                      ))}
                    </Stack>
                  )}
                  {r.false_positive.length > 0 && (
                    <Stack direction="row" gap={0.4} alignItems="center">
                      <Typography variant="caption" color="error" sx={{ fontSize: 10 }}>FP:</Typography>
                      {r.false_positive.map((c) => (
                        <Chip key={c} label={c.replace("CONCEPT_", "")} size="small"
                          color="error" sx={{ fontSize: 9 }} />
                      ))}
                    </Stack>
                  )}
                  {r.false_negative.length > 0 && (
                    <Stack direction="row" gap={0.4} alignItems="center">
                      <Typography variant="caption" color="warning.main" sx={{ fontSize: 10 }}>FN:</Typography>
                      {r.false_negative.map((c) => (
                        <Chip key={c} label={c.replace("CONCEPT_", "")} size="small"
                          color="warning" sx={{ fontSize: 9 }} />
                      ))}
                    </Stack>
                  )}
                  {r.true_positive.length === 0 && r.false_positive.length === 0 && r.false_negative.length === 0 && (
                    <Chip label="탐지 없음 ✓" size="small" color="success" sx={{ fontSize: 10 }} />
                  )}
                </Stack>
              </TableCell>
              <TableCell><F1Bar value={r.f1_score} /></TableCell>
              <TableCell><GradeChip grade={r.grade} /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

// ─────────────────────────────────────────────
// 메인 페이지
// ─────────────────────────────────────────────
export default function ConceptEvalHistoryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const runsQuery = useQuery({
    queryKey: ["concept-eval-runs"],
    queryFn: () => apiGet<EvalRunSummary[]>("/api/v1/admin/concept-eval/runs"),
  });

  const deleteMutation = useMutation({
    mutationFn: (runId: string) => apiDelete(`/api/v1/admin/concept-eval/runs/${runId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["concept-eval-runs"] }),
  });

  const runs = runsQuery.data ?? [];

  // 카테고리별 F1 추이 요약
  const trendMap = new Map<string, number[]>();
  [...runs].reverse().forEach((r) => {
    const key = r.category ?? "전체";
    if (!trendMap.has(key)) trendMap.set(key, []);
    if (r.avg_f1 !== null) trendMap.get(key)!.push(r.avg_f1);
  });

  return (
    <AppShell title="평가 이력">
      <Stack spacing={2}>
        <PageCard title="평가 이력" subtitle="저장된 Concept 탐지 평가 실행 이력입니다.">
          <Stack direction="row" spacing={1.5}>
            <Button variant="outlined" startIcon={<ArrowBackRoundedIcon />}
              onClick={() => router.push("/admin/concept-eval")}>
              평가 페이지로
            </Button>
          </Stack>
        </PageCard>

        {/* F1 추이 요약 */}
        {trendMap.size > 0 && (
          <PageCard title="카테고리별 F1 추이 (최근→과거)">
            <Stack spacing={1}>
              {Array.from(trendMap.entries()).map(([cat, vals]) => (
                <Stack key={cat} direction="row" alignItems="center" spacing={2}>
                  <Typography variant="caption" sx={{ minWidth: 80, color: "text.secondary" }}>{cat}</Typography>
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    {vals.map((v, i) => (
                      <Box key={i} title={`${Math.round(v * 100)}%`}
                        sx={{
                          width: 28, height: 28, borderRadius: "50%", display: "grid", placeItems: "center",
                          bgcolor: v >= 0.9 ? "#2e7d32" : v >= 0.7 ? "#1565c0" : v >= 0.5 ? "#e65100" : "#c62828",
                          color: "#fff", fontSize: 10, fontWeight: 700,
                        }}>
                        {Math.round(v * 100)}
                      </Box>
                    ))}
                    {vals.length >= 2 && (
                      <Typography variant="caption" color={
                        vals[vals.length - 1] > vals[0] ? "success.main" :
                        vals[vals.length - 1] < vals[0] ? "error" : "text.secondary"
                      } sx={{ ml: 1, fontWeight: 600 }}>
                        {vals[vals.length - 1] > vals[0] ? "▲" : vals[vals.length - 1] < vals[0] ? "▼" : "─"}
                        {" "}{Math.abs(Math.round((vals[vals.length - 1] - vals[0]) * 100))}%p
                      </Typography>
                    )}
                  </Stack>
                </Stack>
              ))}
            </Stack>
          </PageCard>
        )}

        {/* 이력 목록 */}
        <PageCard title={`실행 이력 (${runs.length}건)`}>
          {runsQuery.isPending ? (
            <Box sx={{ display: "grid", placeItems: "center", py: 6 }}>
              <CircularProgress />
            </Box>
          ) : runsQuery.isError ? (
            <Alert severity="error">이력을 불러오지 못했습니다.</Alert>
          ) : runs.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
              저장된 이력이 없습니다. 평가 후 &quot;결과 저장&quot;을 클릭해주세요.
            </Typography>
          ) : (
            <Box>
              {/* 헤더 */}
              <Stack direction="row" spacing={2} sx={{ px: 2, pb: 1, borderBottom: "1px solid", borderColor: "divider" }}>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 32 }}>등급</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 160 }}>실행 시각</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 50 }}>유형</Typography>
                <Typography variant="caption" color="text.secondary">F1 점수</Typography>
              </Stack>
              {runs.map((run) => (
                <RunRow key={run.run_id} run={run} onDelete={(id) => deleteMutation.mutate(id)} />
              ))}
            </Box>
          )}
        </PageCard>
      </Stack>
    </AppShell>
  );
}
