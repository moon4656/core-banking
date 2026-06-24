"use client";

import AddRoundedIcon from "@mui/icons-material/AddRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import EditRoundedIcon from "@mui/icons-material/EditRounded";
import HistoryRoundedIcon from "@mui/icons-material/HistoryRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import DownloadRoundedIcon from "@mui/icons-material/DownloadRounded";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Snackbar,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { PageCard } from "@/components/common/PageCard";
import { AppShell } from "@/components/layout/AppShell";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { BatchEvalResponse, CustomQueryRow, EvalQuery, EvalResult, SaveEvalRunRequest } from "@/types/conceptEval";

// ─────────────────────────────────────────────
// 상수
// ─────────────────────────────────────────────
const GRADE_COLOR: Record<string, "success" | "primary" | "warning" | "error" | "default"> = {
  A: "success",
  B: "primary",
  C: "warning",
  D: "error",
  F: "error",
  "-": "default",
};

const ALL_CATEGORIES = "전체";
const ROWS_PER_PAGE = 15;
const EMPTY_FORM: EvalQuery = { category: "", message: "", expected_agents: [] };

const KNOWN_AGENTS = [
  { id: "PRODUCT_AGENT",  label: "PRODUCT — 상품/신청조건" },
  { id: "RATE_AGENT",     label: "RATE — 금리/시뮬레이션" },
  { id: "POLICY_AGENT",   label: "POLICY — 정책/약관" },
  { id: "SEARCH_AGENT",   label: "SEARCH — 서류/상담이력" },
];

// ─────────────────────────────────────────────
// 헬퍼 컴포넌트
// ─────────────────────────────────────────────

function GradeChip({ grade }: { grade: string }) {
  return (
    <Chip label={grade} size="small" color={GRADE_COLOR[grade] ?? "default"}
      sx={{ fontWeight: 700, minWidth: 32 }} />
  );
}

function F1Bar({ value }: { value: number | null }) {
  if (value === null) return <Typography variant="body2" color="text.secondary">-</Typography>;
  const pct = Math.round(value * 100);
  const color = value >= 0.9 ? "#2e7d32" : value >= 0.7 ? "#1565c0" : value >= 0.5 ? "#e65100" : "#c62828";
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box sx={{ width: 60, height: 6, borderRadius: 3, bgcolor: "grey.200", overflow: "hidden" }}>
        <Box sx={{ width: `${pct}%`, height: "100%", bgcolor: color, borderRadius: 3 }} />
      </Box>
      <Typography variant="body2" sx={{ minWidth: 34, color, fontWeight: 600 }}>{pct}%</Typography>
    </Box>
  );
}

function ConceptChips({ concepts, variant }: { concepts: string[]; variant: "tp" | "fp" | "fn" | "neutral" }) {
  const colorMap = { tp: "success", fp: "error", fn: "warning", neutral: "default" } as const;
  if (concepts.length === 0) return <Typography variant="body2" color="text.secondary">-</Typography>;
  return (
    <Stack direction="row" gap={0.5} flexWrap="wrap">
      {concepts.map((c) => (
        <Chip key={c} label={c.replace("CONCEPT_", "")} size="small"
          color={colorMap[variant]} variant={variant === "neutral" ? "outlined" : "filled"}
          sx={{ fontSize: 10 }} />
      ))}
    </Stack>
  );
}

function AgentChip({ agentId, variant }: { agentId: string; variant: "tp" | "fp" | "fn" | "neutral" }) {
  const colorMap = { tp: "success", fp: "error", fn: "warning", neutral: "default" } as const;
  const shortLabel = agentId.replace("_AGENT", "");
  return (
    <Chip label={shortLabel} size="small" color={colorMap[variant]}
      variant={variant === "neutral" ? "outlined" : "filled"} sx={{ fontSize: 10 }} />
  );
}

function ResultCell({ res }: { res: EvalResult | undefined }) {
  if (!res) return <Typography variant="body2" color="text.disabled">미실행</Typography>;

  // expected=[] + routed=[] → 미라우팅 정답
  if (res.expected_agents.length === 0 && res.routed_agents.length === 0) {
    return <Chip label="미라우팅 ✓" size="small" color="success" sx={{ fontSize: 10 }} />;
  }

  const expandedSet = new Set(res.expanded_concepts ?? []);

  return (
    <Stack spacing={0.6}>
      {/* 탐지된 Concept (직접/확장 구분) */}
      {res.detected_concepts.length > 0 && (
        <Stack direction="row" gap={0.4} flexWrap="wrap" alignItems="center">
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 44 }}>Concept:</Typography>
          {res.detected_concepts.map((c) => (
            <Tooltip key={c} title={expandedSet.has(c) ? "온톨로지 확장" : "직접 탐지"}>
              <Chip
                label={c.replace("CONCEPT_", "")}
                size="small"
                variant={expandedSet.has(c) ? "outlined" : "filled"}
                color="default"
                sx={{ fontSize: 9, opacity: expandedSet.has(c) ? 0.7 : 1 }}
              />
            </Tooltip>
          ))}
        </Stack>
      )}

      {/* 라우팅 결과 */}
      {res.routed_agents.length > 0 && (
        <Stack direction="row" gap={0.4} flexWrap="wrap" alignItems="center">
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 44 }}>Agent:</Typography>
          {res.routed_agents.map((a) => (
            <AgentChip key={a} agentId={a} variant="neutral" />
          ))}
        </Stack>
      )}

      {/* TP / FP / FN (Agent 기준) */}
      {res.true_positive.length > 0 && (
        <Stack direction="row" gap={0.4} flexWrap="wrap" alignItems="center">
          <Typography variant="caption" color="success.main" sx={{ minWidth: 44 }}>TP:</Typography>
          {res.true_positive.map((a) => <AgentChip key={a} agentId={a} variant="tp" />)}
        </Stack>
      )}
      {res.false_positive.length > 0 && (
        <Stack direction="row" gap={0.4} flexWrap="wrap" alignItems="center">
          <Typography variant="caption" color="error" sx={{ minWidth: 44 }}>FP:</Typography>
          {res.false_positive.map((a) => <AgentChip key={a} agentId={a} variant="fp" />)}
        </Stack>
      )}
      {res.false_negative.length > 0 && (
        <Stack direction="row" gap={0.4} flexWrap="wrap" alignItems="center">
          <Typography variant="caption" color="warning.main" sx={{ minWidth: 44 }}>FN:</Typography>
          {res.false_negative.map((a) => <AgentChip key={a} agentId={a} variant="fn" />)}
        </Stack>
      )}
    </Stack>
  );
}

function SummaryCard({ evalData }: { evalData: BatchEvalResponse }) {
  const { summary } = evalData;
  const dist = summary.grade_distribution;
  return (
    <PageCard title="평가 요약">
      <Stack direction={{ xs: "column", sm: "row" }} spacing={3}
        divider={<Divider orientation="vertical" flexItem />}>
        <Box sx={{ minWidth: 160 }}>
          <Typography variant="caption" color="text.secondary">전체 평균 F1</Typography>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.5 }}>
            <Typography variant="h4" fontWeight={700}>
              {summary.avg_f1 !== null ? Math.round(summary.avg_f1 * 100) : "-"}
            </Typography>
            <Typography variant="body1" color="text.secondary">%</Typography>
            <GradeChip grade={summary.overall_grade} />
          </Stack>
          <Typography variant="caption" color="text.secondary">총 {summary.total}건</Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">등급 분포</Typography>
          <Stack direction="row" spacing={0.8} sx={{ mt: 0.5 }} flexWrap="wrap">
            {["A", "B", "C", "D", "F"].map((g) =>
              (dist[g] ?? 0) > 0 ? (
                <Chip key={g} label={`${g}: ${dist[g]}`} size="small"
                  color={GRADE_COLOR[g]} sx={{ fontWeight: 600 }} />
              ) : null
            )}
          </Stack>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" color="text.secondary">카테고리별 평균 F1</Typography>
          <Stack spacing={0.3} sx={{ mt: 0.5 }}>
            {Object.entries(summary.by_category).map(([cat, cs]) => (
              <Stack key={cat} direction="row" alignItems="center" spacing={1}>
                <Typography variant="caption" sx={{ minWidth: 90, color: "text.secondary" }}>{cat}</Typography>
                <F1Bar value={cs.avg_f1} />
              </Stack>
            ))}
          </Stack>
        </Box>
      </Stack>
    </PageCard>
  );
}

// ─────────────────────────────────────────────
// 질의 추가/수정 다이얼로그
// ─────────────────────────────────────────────

function AddQueryDialog({
  open,
  onClose,
  onSave,
  categories,
  initial,
  defaultCategory,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (q: EvalQuery) => void;
  categories: string[];
  initial?: EvalQuery;
  defaultCategory?: string;
}) {
  const makeDefault = () =>
    initial ?? { ...EMPTY_FORM, category: defaultCategory && defaultCategory !== ALL_CATEGORIES ? defaultCategory : "" };

  const [form, setForm] = useState<EvalQuery>(makeDefault);
  // freeSolo Autocomplete: inputValue를 별도로 관리해 value와 동기화
  const [categoryInput, setCategoryInput] = useState(form.category);

  // 다이얼로그 열릴 때마다 폼 초기화
  useEffect(() => {
    if (open) {
      const d = makeDefault();
      setForm(d);
      setCategoryInput(d.category);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function handleSave() {
    const finalCategory = categoryInput.trim() || form.category.trim() || "사용자 입력";
    if (!form.message.trim()) return;
    onSave({ ...form, category: finalCategory });
    onClose();
  }

  function handleClose() {
    onClose();
  }

  const catOptions = Array.from(new Set([
    ...categories.filter((c) => c !== ALL_CATEGORIES),
    ...(categoryInput && !categories.includes(categoryInput) ? [categoryInput] : []),
  ]));

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initial ? "질의 수정" : "질의 추가"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {/* 카테고리 — freeSolo + inputValue 분리로 안정적 동작 */}
          <Autocomplete
            freeSolo
            options={catOptions}
            value={form.category}
            inputValue={categoryInput}
            onChange={(_, v) => {
              const val = (v as string) ?? "";
              setForm((f) => ({ ...f, category: val }));
              setCategoryInput(val);
            }}
            onInputChange={(_, v, reason) => {
              setCategoryInput(v);
              if (reason !== "reset") {
                setForm((f) => ({ ...f, category: v }));
              }
            }}
            renderInput={(params) => (
              <TextField {...params} label="카테고리" placeholder="목록 선택 또는 직접 입력" size="small" required />
            )}
          />

          <TextField
            label="질의 메시지"
            placeholder="예: 신용대출 금리 알려줘"
            size="small"
            fullWidth
            required
            autoFocus
            value={form.message}
            onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
            onKeyDown={(e) => { if (e.key === "Enter" && form.message.trim()) handleSave(); }}
          />

          <Autocomplete
            multiple
            options={KNOWN_AGENTS.map((a) => a.id)}
            value={form.expected_agents}
            onChange={(_, v) => setForm((f) => ({ ...f, expected_agents: v }))}
            getOptionLabel={(id) => KNOWN_AGENTS.find((a) => a.id === id)?.label ?? id}
            renderTags={(selected, getTagProps) =>
              selected.map((id, i) => {
                const { key, ...tagProps } = getTagProps({ index: i });
                return (
                  <Chip key={key} label={id.replace("_AGENT", "")} size="small"
                    color="primary" {...tagProps} />
                );
              })
            }
            renderInput={(params) => (
              <TextField {...params} label="기대 Agent"
                placeholder={form.expected_agents.length === 0 ? "미라우팅이 정답이면 비워두세요" : ""}
                size="small"
                helperText="이 질의가 라우팅되어야 할 Agent를 선택하세요. 없으면 비워두세요 (오탐방지/미구현)." />
            )}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} color="inherit">취소</Button>
        <Button onClick={handleSave} variant="contained" disabled={!form.message.trim()}>
          {initial ? "저장" : "추가"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ─────────────────────────────────────────────
// 메인 페이지
// ─────────────────────────────────────────────

export default function ConceptEvalPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeCategory, setActiveCategory] = useState<string>(ALL_CATEGORIES);
  const [rows, setRows] = useState<EvalQuery[]>([]);
  // resultMap: 누적 결과 (전체 실행=교체, 선택 실행=병합)
  const [resultMap, setResultMap] = useState<Map<string, EvalResult>>(new Map());
  // 마지막 실행의 summary (SummaryCard 표시용)
  const [lastSummary, setLastSummary] = useState<BatchEvalResponse | null>(null);
  // 방금 선택 실행으로 업데이트된 메시지 키 (하이라이트용)
  const [freshKeys, setFreshKeys] = useState<Set<string>>(new Set());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<{ globalIdx: number; query: EvalQuery } | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(0);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({ open: false, message: "" });

  // 사전 질의서 로드
  const sheetQuery = useQuery({
    queryKey: ["concept-eval-sheet"],
    queryFn: () => apiGet<EvalQuery[]>("/api/v1/admin/concept-eval/query-sheet"),
  });

  // 커스텀 질의 DB 로드
  const customQueriesQuery = useQuery({
    queryKey: ["concept-eval-custom-queries"],
    queryFn: () => apiGet<CustomQueryRow[]>("/api/v1/admin/concept-eval/custom-queries"),
  });

  // preset + custom 합쳐서 rows 초기화 (데이터 도착 시마다 재구성)
  useEffect(() => {
    const preset = sheetQuery.data ?? [];
    const custom: EvalQuery[] = (customQueriesQuery.data ?? []).map(({ id: _id, ...q }) => q);
    setRows([...preset, ...custom]);
  }, [sheetQuery.data, customQueriesQuery.data]);

  const categories = [ALL_CATEGORIES, ...Array.from(new Set(rows.map((q) => q.category)))];

  // 카테고리 필터 (preset + custom 모두 적용)
  const filteredRowsWithIdx = rows
    .map((q, i) => ({ q, i }))
    .filter(({ q }) => activeCategory === ALL_CATEGORIES || q.category === activeCategory);

  // 페이지 클램프 (필터 변경 시 마지막 페이지 초과 방지)
  const totalFiltered = filteredRowsWithIdx.length;
  const clampedPage = Math.min(page, Math.max(0, Math.ceil(totalFiltered / ROWS_PER_PAGE) - 1));

  const pagedRows = filteredRowsWithIdx.slice(
    clampedPage * ROWS_PER_PAGE,
    (clampedPage + 1) * ROWS_PER_PAGE,
  );

  // 선택 헬퍼 — 키는 global index
  const rk = (globalIdx: number) => `row-${globalIdx}`;
  const filteredKeys = filteredRowsWithIdx.map(({ i }) => rk(i));
  const isAllSelected = filteredKeys.length > 0 && filteredKeys.every((k) => selectedKeys.has(k));
  const isIndeterminate = filteredKeys.some((k) => selectedKeys.has(k)) && !isAllSelected;
  const selectedQueries = rows.filter((_, i) => selectedKeys.has(rk(i)));

  function toggleRow(key: string) {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  function toggleAll() {
    if (isAllSelected) {
      setSelectedKeys((prev) => {
        const next = new Set(prev);
        filteredKeys.forEach((k) => next.delete(k));
        return next;
      });
    } else {
      setSelectedKeys((prev) => new Set([...prev, ...filteredKeys]));
    }
  }

  // 마지막 실행 타입 추적 (저장 시 사용)
  const [lastRunType, setLastRunType] = useState<"ALL" | "SELECTED" | null>(null);

  // 전체 실행 — resultMap 전체 교체
  const runAllMutation = useMutation({
    mutationFn: (queries: EvalQuery[]) =>
      apiPost<BatchEvalResponse>("/api/v1/admin/concept-eval/batch", queries),
    onSuccess: (data) => {
      setResultMap(new Map(data.results.map((r) => [r.message, r])));
      setFreshKeys(new Set());
      setLastSummary(data);
    },
  });

  // 선택 실행 — 기존 resultMap에 병합
  const runSelectedMutation = useMutation({
    mutationFn: (queries: EvalQuery[]) =>
      apiPost<BatchEvalResponse>("/api/v1/admin/concept-eval/batch", queries),
    onSuccess: (data) => {
      const updated = new Set(data.results.map((r) => r.message));
      setResultMap((prev) => {
        const next = new Map(prev);
        data.results.forEach((r) => next.set(r.message, r));
        return next;
      });
      setFreshKeys(updated);
      setLastSummary(data);
    },
  });

  const isPending = runAllMutation.isPending || runSelectedMutation.isPending;
  const isError = runAllMutation.isError || runSelectedMutation.isError;

  // 결과 저장 mutation
  const saveMutation = useMutation({
    mutationFn: (body: SaveEvalRunRequest) =>
      apiPost("/api/v1/admin/concept-eval/runs", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["concept-eval-runs"] });
    },
  });

  function handleRunAll() {
    setFreshKeys(new Set());
    setLastRunType("ALL");
    runAllMutation.mutate(filteredRowsWithIdx.map(({ q }) => q));
  }

  function handleRunSelected() {
    if (selectedQueries.length === 0) return;
    setLastRunType("SELECTED");
    runSelectedMutation.mutate(selectedQueries);
  }

  function handleSave() {
    if (!lastSummary || resultMap.size === 0 || !lastRunType) return;
    const body: SaveEvalRunRequest = {
      run_type: lastRunType,
      category: activeCategory === ALL_CATEGORIES ? null : activeCategory,
      results: Array.from(resultMap.values()),
      summary: lastSummary.summary,
    };
    saveMutation.mutate(body);
  }

  function handleReset() {
    setResultMap(new Map());
    setLastSummary(null);
    setFreshKeys(new Set());
    setSelectedKeys(new Set());
    setLastRunType(null);
    setPage(0);
    // rows는 useEffect가 preset+custom 합쳐서 자동 재구성하므로 별도 리셋 불필요
  }

  // preset 행 수 (커스텀 질의 구분 기준)
  const presetCount = sheetQuery.data?.length ?? 0;
  // 커스텀 질의 DB row id 맵: globalIdx → DB id
  const customIdMap = new Map<number, number>(
    (customQueriesQuery.data ?? []).map((cq, i) => [presetCount + i, cq.id])
  );

  const addCustomMutation = useMutation({
    mutationFn: (q: EvalQuery) => apiPost<CustomQueryRow>("/api/v1/admin/concept-eval/custom-queries", q),
    onSuccess: (saved, q) => {
      queryClient.invalidateQueries({ queryKey: ["concept-eval-custom-queries"] });
      const targetCat = q.category || ALL_CATEGORIES;
      if (activeCategory !== ALL_CATEGORIES && activeCategory !== targetCat) {
        setActiveCategory(targetCat);
        setPage(0);
      }
      setSnackbar({ open: true, message: `"${saved.category}" 카테고리에 질의가 저장됐습니다.` });
    },
  });

  const updateCustomMutation = useMutation({
    mutationFn: ({ id, q }: { id: number; q: EvalQuery }) =>
      apiPut<CustomQueryRow>(`/api/v1/admin/concept-eval/custom-queries/${id}`, q),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["concept-eval-custom-queries"] });
      setSnackbar({ open: true, message: "질의가 수정됐습니다." });
    },
  });

  const deleteCustomMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/api/v1/admin/concept-eval/custom-queries/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["concept-eval-custom-queries"] }),
  });

  function handleAddSave(q: EvalQuery) {
    if (editTarget !== null) {
      const dbId = customIdMap.get(editTarget.globalIdx);
      if (dbId !== undefined) {
        // 커스텀 질의: DB PUT
        updateCustomMutation.mutate({ id: dbId, q });
      } else {
        // 프리셋 행 수정: 로컬 state만 업데이트
        setRows((prev) => prev.map((r, i) => (i === editTarget.globalIdx ? q : r)));
        setSnackbar({ open: true, message: "질의가 수정됐습니다." });
      }
      setEditTarget(null);
    } else {
      // 신규 추가: DB POST
      addCustomMutation.mutate(q);
    }
    setResultMap(new Map());
    setLastSummary(null);
  }

  function handleEdit(globalIdx: number) {
    setEditTarget({ globalIdx, query: rows[globalIdx] });
    setDialogOpen(true);
  }

  function handleDelete(globalIdx: number) {
    const dbId = customIdMap.get(globalIdx);
    if (dbId !== undefined) {
      deleteCustomMutation.mutate(dbId);
    } else {
      // 프리셋 행: 로컬 state에서만 제거 (새로고침하면 복원됨)
      setRows((prev) => prev.filter((_, i) => i !== globalIdx));
    }
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      next.delete(rk(globalIdx));
      return next;
    });
    setResultMap(new Map());
    setLastSummary(null);
  }

  function handleExportCsv() {
    if (resultMap.size === 0) return;
    const header = "카테고리,질의,기대Agent,라우팅Agent,탐지Concept,TP,FP,FN,Precision,Recall,F1,등급\n";
    const csvRows = Array.from(resultMap.values()).map((r) =>
      [r.category, `"${r.message}"`, r.expected_agents.join("|"), r.routed_agents.join("|"),
        r.detected_concepts.join("|"), r.true_positive.join("|"), r.false_positive.join("|"),
        r.false_negative.join("|"), r.precision ?? "", r.recall ?? "", r.f1_score ?? "", r.grade].join(",")
    );
    const blob = new Blob(["﻿" + header + csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `concept_eval_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell title="Concept 탐지 평가">
      <Stack spacing={2}>
        {/* 액션 바 */}
        <PageCard title="Concept 탐지 평가"
          subtitle="질의별로 탐지된 Concept을 기대값과 비교해 F1 점수와 등급으로 평가합니다.">
          <Stack direction="row" spacing={1.5} flexWrap="wrap">
            <Button variant="contained"
              startIcon={runAllMutation.isPending
                ? <CircularProgress size={16} color="inherit" />
                : <PlayArrowRoundedIcon />}
              onClick={handleRunAll}
              disabled={isPending || totalFiltered === 0}>
              {runAllMutation.isPending ? "평가 중..." : `전체 실행 (${totalFiltered}건)`}
            </Button>
            <Button variant="outlined" color="primary"
              startIcon={runSelectedMutation.isPending
                ? <CircularProgress size={16} color="inherit" />
                : <PlayArrowRoundedIcon />}
              onClick={handleRunSelected}
              disabled={isPending || selectedQueries.length === 0}>
              {runSelectedMutation.isPending ? "실행 중..." : `선택 실행 (${selectedQueries.length}건)`}
            </Button>
            <Button variant="outlined" startIcon={<AddRoundedIcon />}
              onClick={() => { setEditTarget(null); setDialogOpen(true); }}>
              질의 추가
            </Button>
            <Button variant="outlined" startIcon={<RefreshRoundedIcon />} onClick={handleReset}>
              초기화
            </Button>
            {resultMap.size > 0 && (
              <Button variant="outlined" color="success"
                startIcon={saveMutation.isPending
                  ? <CircularProgress size={16} color="inherit" />
                  : <SaveRoundedIcon />}
                onClick={handleSave}
                disabled={saveMutation.isPending}>
                {saveMutation.isSuccess ? "저장됨 ✓" : "결과 저장"}
              </Button>
            )}
            {resultMap.size > 0 && (
              <Button variant="outlined" startIcon={<DownloadRoundedIcon />} onClick={handleExportCsv}>
                CSV 내보내기
              </Button>
            )}
            <Button variant="outlined" startIcon={<HistoryRoundedIcon />}
              onClick={() => router.push("/admin/concept-eval/history")}>
              이력 보기
            </Button>
          </Stack>
        </PageCard>

        {isError && <Alert severity="error">평가 실행 중 오류가 발생했습니다.</Alert>}
        {lastSummary && <SummaryCard evalData={lastSummary} />}

        {/* 카테고리 탭 */}
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={activeCategory}
            onChange={(_, v) => {
              setActiveCategory(v as string);
              setSelectedKeys(new Set());
              setFreshKeys(new Set());
              setPage(0);
            }}
            variant="scrollable" scrollButtons="auto">
            {categories.map((cat) => <Tab key={cat} label={cat} value={cat} />)}
          </Tabs>
        </Box>

        {/* 테이블 */}
        <PageCard title="질의 목록 및 탐지 결과">
          {sheetQuery.isPending ? (
            <Box sx={{ display: "grid", placeItems: "center", py: 6 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small" sx={{ minWidth: 900 }}>
                  <TableHead>
                    <TableRow sx={{ "& th": { fontWeight: 700, bgcolor: "grey.50" } }}>
                      <TableCell padding="checkbox" sx={{ width: 44 }}>
                        <Checkbox
                          size="small"
                          checked={isAllSelected}
                          indeterminate={isIndeterminate}
                          onChange={toggleAll}
                        />
                      </TableCell>
                      <TableCell sx={{ width: 110 }}>카테고리</TableCell>
                      <TableCell sx={{ minWidth: 220 }}>질의 메시지</TableCell>
                      <TableCell sx={{ minWidth: 160 }}>기대 Agent</TableCell>
                      <TableCell sx={{ minWidth: 200 }}>라우팅 결과</TableCell>
                      <TableCell sx={{ width: 80 }}>F1</TableCell>
                      <TableCell sx={{ width: 56 }}>등급</TableCell>
                      <TableCell sx={{ width: 80 }} />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pagedRows.map(({ q, i }) => {
                      const key = rk(i);
                      const checked = selectedKeys.has(key);
                      const res = resultMap.get(q.message);
                      const isPreset = i < presetCount;
                      const isFresh = freshKeys.has(q.message);
                      return (
                        <TableRow key={key} hover selected={checked}
                          sx={{
                            verticalAlign: "top", cursor: "pointer",
                            ...(isFresh && !checked && {
                              bgcolor: "rgba(25, 118, 210, 0.06)",
                              outline: "1px solid rgba(25,118,210,0.25)",
                            }),
                          }}
                          onClick={() => toggleRow(key)}>
                          <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                            <Checkbox size="small" checked={checked} onChange={() => toggleRow(key)} />
                          </TableCell>
                          <TableCell>
                            <Chip label={q.category} size="small"
                              color={isPreset ? "default" : "primary"}
                              variant="outlined" sx={{ fontSize: 10 }} />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{q.message}</Typography>
                          </TableCell>
                          <TableCell>
                            {q.expected_agents.length === 0
                              ? <Chip label="없음 (미라우팅)" size="small" color="default" sx={{ fontSize: 10 }} />
                              : <Stack direction="row" gap={0.5} flexWrap="wrap">
                                  {q.expected_agents.map((a) => (
                                    <AgentChip key={a} agentId={a} variant="neutral" />
                                  ))}
                                </Stack>}
                          </TableCell>
                          <TableCell><ResultCell res={res} /></TableCell>
                          <TableCell>
                            {res ? <F1Bar value={res.f1_score} />
                              : <Typography variant="body2" color="text.disabled">-</Typography>}
                          </TableCell>
                          <TableCell>
                            {res ? <GradeChip grade={res.grade} />
                              : <Typography variant="body2" color="text.disabled">-</Typography>}
                          </TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <Stack direction="row">
                              <Tooltip title="수정">
                                <IconButton size="small" onClick={() => handleEdit(i)}>
                                  <EditRoundedIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="삭제">
                                <IconButton size="small" onClick={() => handleDelete(i)} color="error">
                                  <DeleteOutlineRoundedIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Stack>
                          </TableCell>
                        </TableRow>
                      );
                    })}

                    {totalFiltered === 0 && (
                      <TableRow>
                        <TableCell colSpan={8} sx={{ textAlign: "center", py: 4 }}>
                          <Typography color="text.secondary">질의 데이터가 없습니다.</Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </Box>

              {totalFiltered > ROWS_PER_PAGE && (
                <TablePagination
                  component="div"
                  count={totalFiltered}
                  page={clampedPage}
                  onPageChange={(_, newPage) => setPage(newPage)}
                  rowsPerPage={ROWS_PER_PAGE}
                  rowsPerPageOptions={[ROWS_PER_PAGE]}
                  labelDisplayedRows={({ from, to, count }) => `${from}–${to} / ${count}건`}
                />
              )}
            </>
          )}
        </PageCard>

        {/* 범례 */}
        <PageCard title="범례">
          <Stack direction="row" spacing={2} flexWrap="wrap">
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Chip label="TP" size="small" color="success" sx={{ fontSize: 10 }} />
              <Typography variant="caption">기대한 Agent로 라우팅됨 (정답)</Typography>
            </Stack>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Chip label="FP" size="small" color="error" sx={{ fontSize: 10 }} />
              <Typography variant="caption">기대 안 했는데 라우팅됨 (오라우팅)</Typography>
            </Stack>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Chip label="FN" size="small" color="warning" sx={{ fontSize: 10 }} />
              <Typography variant="caption">기대했지만 라우팅 안 됨 (미라우팅)</Typography>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              {["A", "B", "C", "D", "F"].map((g) => <GradeChip key={g} grade={g} />)}
              <Typography variant="caption">A≥90% / B≥70% / C≥50% / D≥30% / F&lt;30%</Typography>
            </Stack>
          </Stack>
        </PageCard>
      </Stack>

      {/* 질의 추가/수정 다이얼로그 */}
      <AddQueryDialog
        open={dialogOpen}
        onClose={() => { setDialogOpen(false); setEditTarget(null); }}
        onSave={handleAddSave}
        categories={categories}
        initial={editTarget?.query}
        defaultCategory={activeCategory}
      />

      {/* 추가/수정 완료 알림 */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        message={snackbar.message}
      />
    </AppShell>
  );
}
