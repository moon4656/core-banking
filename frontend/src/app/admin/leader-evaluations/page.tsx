"use client";

import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import VerifiedRoundedIcon from "@mui/icons-material/VerifiedRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import DeleteRoundedIcon from "@mui/icons-material/DeleteRounded";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  LinearProgress,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { GridColDef, GridRowParams } from "@mui/x-data-grid";
import { useMemo, useState } from "react";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { ApiError, apiDelete, apiGet } from "@/lib/api";
import {
  LeaderEvaluationDetail,
  LeaderEvaluationEvidence,
  LeaderEvaluationListItem,
  LeaderEvaluationListResponse,
  LeaderEvaluationTraceEvent,
  ScoreBreakdown,
} from "@/types/leaderEvaluation";

// ─────────────────────────────────────────────
// 헬퍼 컴포넌트
// ─────────────────────────────────────────────

const INTENT_COLORS: Record<string, "primary" | "secondary" | "success" | "warning" | "default"> = {
  INQUIRY: "primary",
  COMPARISON: "secondary",
  RECOMMENDATION: "success",
  APPLICATION: "warning",
  OTHER: "default",
};

function IntentChip({ intent }: { intent: string | null }) {
  if (!intent) return <Chip label="-" size="small" />;
  return <Chip label={intent} size="small" color={INTENT_COLORS[intent] ?? "default"} />;
}

const RESULT_COLORS: Record<string, "success" | "warning" | "error" | "default"> = {
  PASS: "success",
  NEEDS_REVIEW: "warning",
  FAIL: "error",
  BLOCKED: "default",
};

function ResultChip({ result }: { result: string | null }) {
  if (!result) return <Chip label="-" size="small" />;
  return <Chip label={result} size="small" color={RESULT_COLORS[result] ?? "default"} />;
}

const REVIEW_REASON_LABELS: Record<string, string> = {
  BLOCKED: "시스템 오류로 처리 불완전",
  TOOL_FAILED: "Tool 호출 실패",
  NO_EVIDENCE: "근거 데이터 없음",
  NO_CONCEPT_DETECTED: "Concept 미탐지",
  UNROUTED_CONCEPTS: "라우팅 불가 Concept 존재",
  MISSING_DIRECT_EVIDENCE: "직접 탐지 Concept 근거 없음",
  LOW_EVIDENCE_QUALITY: "근거 품질 낮음",
  LOW_LEADER_CONFIDENCE: "Leader 신뢰도 낮음",
};

function ReviewReasonText({ code }: { code: string | null }) {
  if (!code) return <Typography variant="body2" color="text.secondary">-</Typography>;
  return (
    <Typography variant="body2" color="warning.main">
      {REVIEW_REASON_LABELS[code] ?? code}
    </Typography>
  );
}

function AgentChips({ agents }: { agents: string[] }) {
  const MAX_SHOW = 2;
  if (!agents.length) return <Typography variant="body2" color="text.secondary">-</Typography>;
  return (
    <Stack direction="row" spacing={0.5} flexWrap="wrap">
      {agents.slice(0, MAX_SHOW).map((a) => (
        <Chip key={a} label={a.replace("_AGENT", "")} size="small" variant="outlined" />
      ))}
      {agents.length > MAX_SHOW && (
        <Chip label={`+${agents.length - MAX_SHOW}`} size="small" />
      )}
    </Stack>
  );
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  const pct = value != null ? Math.round(value * 100) : 0;
  const color = pct >= 80 ? "success" : pct >= 60 ? "warning" : "error";
  return (
    <Box>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="caption">{label}</Typography>
        <Typography variant="caption">{value != null ? value.toFixed(3) : "-"}</Typography>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={pct}
        color={color}
        sx={{ height: 6, borderRadius: 3 }}
      />
    </Box>
  );
}

function ScoreBreakdownPanel({ sb }: { sb: ScoreBreakdown }) {
  return (
    <Stack spacing={0.75}>
      <ScoreBar label="Intent" value={sb.intent_score} />
      <ScoreBar label="Concept" value={sb.concept_score} />
      <ScoreBar label="Routing" value={sb.routing_score} />
      <ScoreBar label="Tool" value={sb.tool_success_score} />
      <ScoreBar label="Evidence" value={sb.evidence_score} />
      <Box sx={{ borderTop: "1px dashed", borderColor: "divider", pt: 0.5 }}>
        <ScoreBar label="Final" value={sb.final_score} />
      </Box>
    </Stack>
  );
}

// ─────────────────────────────────────────────
// TraceTimeline
// ─────────────────────────────────────────────

function summarizeEvent(event: LeaderEvaluationTraceEvent): string {
  const od = event.output_data ?? {};
  const id = event.input_data ?? {};
  switch (event.event_type) {
    case "REQUEST_RECEIVED":
      return `메시지: "${String(id.message ?? "").slice(0, 40)}"`;
    case "MEMORY_LOADED":
      return `Short Memory ${od.turns_loaded ?? 0}턴 로드`;
    case "LTM_LOADED":
      return `LTM ${od.ltm_turns_loaded ?? 0}턴 로드`;
    case "INTENT_ANALYZED":
      return `Intent=${od.intent ?? "-"}, keywords=${JSON.stringify(od.keywords ?? [])}`;
    case "CONCEPT_DETECTED":
      return `직접탐지 ${(od.detected_concepts as string[] | undefined)?.length ?? 0}개, 확장 ${(od.expanded_concepts as string[] | undefined)?.length ?? 0}개`;
    case "AGENT_SELECTED":
      return `라우팅: ${(od.routed_agents as string[] | undefined)?.join(", ") ?? "-"}`;
    case "PLAN_CREATED":
      return `${od.step_count ?? 0}개 step 계획 생성`;
    case "TOOL_INVOKED":
      return `${event.tool_id ?? id.api_id ?? "-"} (${event.agent_id ?? "-"}) → ${od.status ?? "-"}`;
    case "RESULTS_RERANKED":
      return `${od.success_count ?? 0}개 성공 결과 재정렬`;
    case "RESPONSE_COMPLETED":
      return `응답 완료`;
    default:
      return event.event_type;
  }
}

function TraceTimeline({ events }: { events: LeaderEvaluationTraceEvent[] }) {
  const [openJson, setOpenJson] = useState<LeaderEvaluationTraceEvent | null>(null);

  if (!events.length) {
    return (
      <Alert severity="warning">
        Trace 데이터가 없습니다. 마이그레이션 상태 또는 요청 처리 오류를 확인하세요.
      </Alert>
    );
  }

  return (
    <>
      <Stack spacing={0.5}>
        {events.map((ev) => {
          const isError = ev.status !== "success";
          const isSlow = ev.duration_ms != null && ev.duration_ms > 5000;
          const isMedium = !isSlow && ev.duration_ms != null && ev.duration_ms > 1000;
          const bgColor = isSlow
            ? "error.50"
            : isMedium
            ? "warning.50"
            : isError
            ? "error.50"
            : undefined;

          return (
            <Box
              key={ev.id}
              sx={{
                display: "flex",
                alignItems: "flex-start",
                gap: 1,
                p: 0.75,
                borderRadius: 1,
                bgcolor: bgColor,
                cursor: "pointer",
                "&:hover": { bgcolor: "action.hover" },
              }}
              onClick={() => setOpenJson(ev)}
            >
              <Box sx={{ mt: 0.25 }}>
                {isError ? (
                  <ErrorOutlineRoundedIcon fontSize="small" color="error" />
                ) : (
                  <CheckCircleOutlineRoundedIcon fontSize="small" color={isSlow ? "warning" : "success"} />
                )}
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="caption" fontWeight={600} noWrap>
                    {ev.event_type}
                  </Typography>
                  {ev.duration_ms != null && (
                    <Chip
                      label={`${ev.duration_ms}ms`}
                      size="small"
                      color={isSlow ? "error" : isMedium ? "warning" : "default"}
                      sx={{ height: 18, fontSize: "0.65rem" }}
                    />
                  )}
                </Stack>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {summarizeEvent(ev)}
                </Typography>
              </Box>
            </Box>
          );
        })}
      </Stack>

      <Dialog open={!!openJson} onClose={() => setOpenJson(null)} maxWidth="md" fullWidth>
        <DialogTitle>{openJson?.event_type} — 상세 데이터</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Input</Typography>
          <Box
            component="pre"
            sx={{ bgcolor: "grey.100", p: 1.5, borderRadius: 1, overflowX: "auto", fontSize: "0.75rem" }}
          >
            {JSON.stringify(openJson?.input_data, null, 2)}
          </Box>
          <Typography variant="subtitle2" sx={{ mt: 1.5, mb: 0.5 }}>Output</Typography>
          <Box
            component="pre"
            sx={{ bgcolor: "grey.100", p: 1.5, borderRadius: 1, overflowX: "auto", fontSize: "0.75rem" }}
          >
            {JSON.stringify(openJson?.output_data, null, 2)}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ─────────────────────────────────────────────
// 기타 유틸
// ─────────────────────────────────────────────

function formatNullable(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Y" : "N";
  return String(value);
}

function renderTagList(items: string[], emptyLabel: string, color?: "primary" | "warning" | "error" | "default") {
  if (!items.length) {
    return <Typography variant="body2" color="text.secondary">{emptyLabel}</Typography>;
  }
  return (
    <Stack direction="row" gap={0.75} flexWrap="wrap">
      {items.map((item) => (
        <Chip key={item} label={item} size="small" color={color ?? "default"} />
      ))}
    </Stack>
  );
}

// ─────────────────────────────────────────────
// 날짜 포맷 헬퍼
// ─────────────────────────────────────────────

function formatDatetime(raw: string | null | undefined): string {
  if (!raw) return "-";
  try {
    // DB는 UTC naive datetime("2026-06-12 11:22:51")을 저장 → 'Z' 붙여 UTC로 파싱
    // getHours()는 브라우저 로컬 시간(KST = UTC+9)으로 자동 변환됨
    const utcStr = raw.replace(" ", "T") + "Z";
    const d = new Date(utcStr);
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${mm}/${dd} ${hh}:${mi}`;
  } catch {
    return raw.slice(0, 16);
  }
}

const eventColumns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 70 },
  { field: "event_type", headerName: "Event", minWidth: 180, flex: 1 },
  { field: "agent_id", headerName: "Agent", minWidth: 140, flex: 0.8 },
  { field: "tool_id", headerName: "Tool", minWidth: 140, flex: 0.8 },
  { field: "status", headerName: "Status", width: 100 },
  { field: "duration_ms", headerName: "Latency(ms)", width: 110 },
];

const evidenceColumns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 70 },
  {
    field: "concept_short",
    headerName: "Concept",
    minWidth: 160,
    flex: 1,
  },
  { field: "agent_id", headerName: "Agent", width: 130 },
  { field: "source_id", headerName: "Source", minWidth: 160, flex: 0.8 },
  { field: "confidence_score", headerName: "Conf", width: 90 },
  { field: "data_quality_score", headerName: "Quality", width: 90 },
  { field: "intent_relevance_score", headerName: "Intent", width: 90 },
  { field: "item_count", headerName: "Items", width: 70 },
];

// ─────────────────────────────────────────────
// 페이지
// ─────────────────────────────────────────────

export default function LeaderEvaluationsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [requestIdKeyword, setRequestIdKeyword] = useState("");
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [showTimeline, setShowTimeline] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["leader-evaluation-list", requestIdKeyword],
    queryFn: () =>
      apiGet<LeaderEvaluationListResponse>(
        `/api/v1/admin/leader-evaluations${
          requestIdKeyword ? `?request_id=${encodeURIComponent(requestIdKeyword)}` : ""
        }`
      ),
  });

  const deleteMutation = useMutation({
    mutationFn: (requestId: string) =>
      apiDelete<{ deleted: boolean }>(`/api/v1/admin/leader-evaluations/${requestId}`),
    onSuccess: (_, requestId) => {
      if (selectedRequestId === requestId) setSelectedRequestId(null);
      setDeleteTarget(null);
      listQuery.refetch();
    },
    onError: () => setDeleteTarget(null),
  });

  const detailQuery = useQuery({
    queryKey: ["leader-evaluation-detail", selectedRequestId],
    queryFn: () =>
      apiGet<LeaderEvaluationDetail>(`/api/v1/admin/leader-evaluations/${selectedRequestId}`),
    enabled: !!selectedRequestId,
  });

  const listError = listQuery.error instanceof ApiError ? listQuery.error.detail : null;
  const detailError = detailQuery.error instanceof ApiError ? detailQuery.error.detail : null;

  const listRows = useMemo(
    () =>
      (listQuery.data?.items ?? []).map((item: LeaderEvaluationListItem) => ({
        id: item.request_id,
        ...item,
        concept_count: `${item.detected_concepts.length}개`,
        final_score:
          item.score_breakdown?.final_score?.toFixed(3) ??
          item.leader_confidence_score?.toFixed(3) ??
          "-",
      })),
    [listQuery.data]
  );

  const listColumns = useMemo<GridColDef[]>(
    () => [
      {
        field: "created_at",
        headerName: "일시",
        width: 95,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
            <Typography sx={{ fontSize: "0.72rem", color: "text.secondary", lineHeight: 1.3 }}>
              {formatDatetime(params.value as string)}
            </Typography>
          </Box>
        ),
      },
      {
        field: "user_question",
        headerName: "질문",
        minWidth: 180,
        flex: 1.2,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%", width: "100%", overflow: "hidden" }}>
            <Tooltip title={String(params.value ?? "")}>
              <Typography variant="body2" noWrap sx={{ width: "100%" }}>
                {params.value
                  ? String(params.value).slice(0, 50) + (String(params.value).length > 50 ? "…" : "")
                  : "-"}
              </Typography>
            </Tooltip>
          </Box>
        ),
      },
      {
        field: "detected_intent",
        headerName: "Intent",
        width: 120,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
            <IntentChip intent={params.value} />
          </Box>
        ),
      },
      {
        field: "selected_agents",
        headerName: "Agents",
        minWidth: 160,
        flex: 0.8,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
            <AgentChips agents={params.value ?? []} />
          </Box>
        ),
      },
      {
        field: "final_score",
        headerName: "Score",
        width: 80,
      },
      {
        field: "overall_result",
        headerName: "Status",
        width: 110,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
            <ResultChip result={params.value} />
          </Box>
        ),
      },
      {
        field: "review_reason",
        headerName: "원인",
        minWidth: 150,
        flex: 0.8,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
            <ReviewReasonText code={params.value} />
          </Box>
        ),
      },
      {
        field: "_delete",
        headerName: "",
        width: 52,
        sortable: false,
        disableColumnMenu: true,
        renderCell: (params) => (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", width: "100%" }}>
            <Tooltip title="삭제">
              <IconButton
                size="small"
                color="error"
                onClick={(e) => {
                  e.stopPropagation();
                  setDeleteTarget(String(params.row.request_id));
                }}
              >
                <DeleteRoundedIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
    ],
    []
  );

  const detail = detailQuery.data;
  const eventRows = (detail?.trace_events ?? []) as LeaderEvaluationTraceEvent[];
  const evidenceRows = useMemo(
    () =>
      (detail?.evidences ?? []).map((ev: LeaderEvaluationEvidence) => ({
        ...ev,
        concept_short: (ev.concept_id ?? "").replace("CONCEPT_", ""),
      })),
    [detail]
  );

  function handleSelectRow(params: GridRowParams) {
    setSelectedRequestId(String(params.row.request_id));
    setShowTimeline(false);
  }

  const ld = detail?.leader_decision;
  const es = detail?.evidence_summary;
  const overallResult = detail?.review.overall_result;

  return (
    <AppShell title="리더 평가">
      <Stack spacing={2}>
        {/* 검색 */}
        <PageCard
          title="리더 Agent 평가 조회"
          subtitle="리더의 의도 분류, concept 탐지, agent 선택, 근거 품질을 한 화면에서 점검합니다."
        >
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField
              fullWidth
              label="Request ID 검색"
              placeholder="부분 request_id로 필터링"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") setRequestIdKeyword(searchInput.trim()); }}
            />
            <Button
              variant="contained"
              startIcon={<SearchRoundedIcon />}
              onClick={() => setRequestIdKeyword(searchInput.trim())}
            >
              조회
            </Button>
          </Stack>
        </PageCard>

        {listError ? <Alert severity="error">{listError}</Alert> : null}
        {detailError ? <Alert severity="error">{detailError}</Alert> : null}

        {/* 목록 + 요약 */}
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 400px" },
            alignItems: "stretch",
          }}
        >
          {/* 목록 */}
          <Box>
            {listQuery.isLoading && <LinearProgress sx={{ mb: 1 }} />}
            {!listQuery.isLoading && listRows.length === 0 && !listError && (
              <Alert severity="info" sx={{ mb: 1 }}>
                조회 결과가 없습니다. Request ID 검색어를 확인하거나 채팅 요청을 먼저 실행하세요.
              </Alert>
            )}
            <BaseDataGrid rows={listRows} columns={listColumns} height={520} onRowClick={handleSelectRow} />
          </Box>

          {/* 요약 카드 */}
          <Card
            elevation={0}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: "24px",
              backgroundColor: overallResult === "BLOCKED" ? "grey.50" : "background.paper",
              boxShadow: "0 1px 2px rgba(17, 24, 39, 0.04)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <CardContent sx={{ p: { xs: 2, md: 2.5 }, display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
              <Typography variant="h6">요약</Typography>
              <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2 }}>
                선택한 요청의 자동 평가 결과를 빠르게 확인합니다.
              </Typography>
              {detailQuery.isLoading && <LinearProgress sx={{ mb: 1 }} />}
              <Box sx={{ flex: 1, overflowY: "auto" }}>
                {detail ? (
                  <Stack spacing={2}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <VerifiedRoundedIcon color="primary" fontSize="small" />
                      <Typography fontWeight={600} variant="body2" noWrap>{detail.request_id}</Typography>
                    </Stack>

                    <Typography variant="body2">
                      <strong>질문:</strong> {detail.user_question ?? "-"}
                    </Typography>

                    {/* 최종 답변 */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 0.5 }}>최종 답변</Typography>
                      {detail.answer ? (
                        <Typography variant="body2" color="text.secondary" sx={{ maxHeight: 80, overflowY: "auto" }}>
                          {detail.answer}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.disabled">
                          답변이 저장되지 않았습니다.
                        </Typography>
                      )}
                    </Box>

                    {/* 상태 */}
                    <Stack direction="row" spacing={1} alignItems="center">
                      <ResultChip result={overallResult ?? null} />
                      {detail.leader_decision.review_reason && (
                        <ReviewReasonText code={detail.leader_decision.review_reason} />
                      )}
                    </Stack>

                    {/* Score Breakdown */}
                    {ld?.score_breakdown && (
                      <Box>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Score Breakdown</Typography>
                        <ScoreBreakdownPanel sb={ld.score_breakdown} />
                      </Box>
                    )}

                    <Stack direction="row" spacing={2}>
                      <Typography variant="body2">Memory: {ld?.memory_turns ?? 0}턴</Typography>
                      <Typography variant="body2">LTM: {ld?.ltm_turns ?? 0}턴</Typography>
                    </Stack>
                  </Stack>
                ) : (
                  <Typography color="text.secondary">목록에서 요청을 선택하면 평가 요약이 표시됩니다.</Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* 리더 판단 + Evidence Summary */}
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", xl: "repeat(2, minmax(0, 1fr))" },
          }}
        >
          {/* 리더 판단 */}
          <PageCard title="리더 판단" subtitle="의도, concept, agent 선택과 step 성공률을 함께 봅니다.">
            {detail && ld ? (
              <Stack spacing={2}>
                {/* Intent */}
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="subtitle2">Intent:</Typography>
                  <IntentChip intent={ld.detected_intent} />
                  {ld.intent_urgency && (
                    <Chip label={`긴급도: ${ld.intent_urgency}`} size="small" variant="outlined" />
                  )}
                </Stack>

                {/* Keywords */}
                {ld.intent_keywords.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 0.5 }}>키워드</Typography>
                    {renderTagList(ld.intent_keywords, "", "primary")}
                  </Box>
                )}

                {/* Steps */}
                <Typography variant="body2">
                  Steps: {ld.successful_step_count} 성공 / {ld.failed_step_count} 실패 / {ld.step_count} 전체
                </Typography>

                {/* Direct Concepts */}
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 0.5 }}>직접 탐지 Concept</Typography>
                  {ld.direct_concepts.length > 0
                    ? renderTagList(ld.direct_concepts, "", "primary")
                    : <Typography variant="body2" color="text.secondary">없음</Typography>
                  }
                </Box>

                {/* Expanded Concepts */}
                {ld.expanded_concepts.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 0.5 }}>온톨로지 확장 Concept</Typography>
                    {renderTagList(ld.expanded_concepts, "")}
                  </Box>
                )}

                {/* Unrouted Concepts */}
                {ld.unrouted_concepts.length > 0 && (
                  <Box>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                      <WarningAmberRoundedIcon fontSize="small" color="warning" />
                      <Typography variant="subtitle2" color="warning.main">라우팅 불가 Concept</Typography>
                    </Stack>
                    {renderTagList(ld.unrouted_concepts, "", "warning")}
                  </Box>
                )}

                {/* Selected Agents */}
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 0.5 }}>선택된 Agents</Typography>
                  {renderTagList(ld.selected_agents, "선택된 agent가 없습니다.")}
                </Box>

                {/* Score Breakdown */}
                {ld.score_breakdown && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 0.75 }}>Score Breakdown</Typography>
                    <ScoreBreakdownPanel sb={ld.score_breakdown} />
                  </Box>
                )}
              </Stack>
            ) : (
              <Typography color="text.secondary">선택한 요청의 리더 판단 결과가 여기에 표시됩니다.</Typography>
            )}
          </PageCard>

          {/* Evidence Summary */}
          <PageCard title="Evidence Summary" subtitle="근거 품질 점수와 리뷰 상태를 같이 봅니다.">
            {detail && es ? (
              <Stack spacing={2}>
                <Typography variant="body2">
                  Evidence: {es.evidence_count}건
                </Typography>

                <Stack spacing={0.75}>
                  <ScoreBar label="Avg Confidence" value={es.avg_evidence_confidence} />
                  <ScoreBar label="Data Quality" value={es.avg_data_quality_score} />
                  <ScoreBar label="Intent Relevance" value={es.avg_intent_relevance_score} />
                  {es.grounding_score != null && (
                    <Box>
                      <ScoreBar label="Grounding (추정값)" value={es.grounding_score} />
                    </Box>
                  )}
                </Stack>

                {/* Review Flags */}
                {es.review_flags.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Review Flags</Typography>
                    <Stack spacing={0.5}>
                      {es.review_flags.map((flag) => (
                        <Alert key={flag} severity="warning" sx={{ py: 0.25, px: 1 }}>
                          <Typography variant="caption">{flag}</Typography>
                        </Alert>
                      ))}
                    </Stack>
                  </Box>
                )}

                {/* Missing Concepts */}
                {es.missing_concepts.length > 0 && (
                  <Box>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                      <WarningAmberRoundedIcon fontSize="small" color="warning" />
                      <Typography variant="subtitle2" color="warning.main">근거 없는 Concept</Typography>
                    </Stack>
                    {renderTagList(es.missing_concepts, "", "warning")}
                  </Box>
                )}

                <Typography variant="body2">
                  Hallucination: {formatNullable(detail.review.hallucination_yn)}
                </Typography>
                <Typography variant="body2">
                  Comment: {detail.review.review_comment ?? "등록된 리뷰 코멘트가 없습니다."}
                </Typography>
              </Stack>
            ) : (
              <Typography color="text.secondary">선택한 요청의 근거 요약이 여기에 표시됩니다.</Typography>
            )}
          </PageCard>
        </Box>

        {/* Trace + Evidence 그리드 */}
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", xl: "repeat(2, minmax(0, 1fr))" },
          }}
        >
          {/* Trace */}
          <PageCard title="Trace Events" subtitle="리더와 서브 에이전트의 실행 흐름을 순서대로 확인합니다.">
            {selectedRequestId && (
              <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                <Button
                  size="small"
                  variant={showTimeline ? "outlined" : "contained"}
                  onClick={() => setShowTimeline(false)}
                >
                  그리드
                </Button>
                <Button
                  size="small"
                  variant={showTimeline ? "contained" : "outlined"}
                  onClick={() => setShowTimeline(true)}
                >
                  타임라인
                </Button>
              </Stack>
            )}
            {showTimeline ? (
              <Box sx={{ maxHeight: 360, overflowY: "auto" }}>
                <TraceTimeline events={eventRows} />
              </Box>
            ) : (
              <>
                {!eventRows.length && selectedRequestId && !detailQuery.isLoading && (
                  <Alert severity="warning" sx={{ mb: 1 }}>
                    Trace 데이터가 없습니다. 마이그레이션 완료 여부 또는 요청 처리 오류를 확인하세요.
                  </Alert>
                )}
                <BaseDataGrid rows={eventRows} columns={eventColumns} height={360} />
              </>
            )}
          </PageCard>

          {/* Evidence */}
          <PageCard title="Evidence" subtitle="API 근거와 품질 점수를 비교해봅니다.">
            {!evidenceRows.length && selectedRequestId && !detailQuery.isLoading && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                근거 데이터가 없습니다. Tool 호출이 실패했거나 Mock API가 중단됐을 수 있습니다.
              </Alert>
            )}
            <BaseDataGrid rows={evidenceRows} columns={evidenceColumns} height={360} />
          </PageCard>
        </Box>
      </Stack>

      {/* 삭제 확인 다이얼로그 */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>평가 기록 삭제</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 1 }}>
            아래 요청의 Trace, Evidence, LeaderDecision 기록이 모두 삭제됩니다.
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ wordBreak: "break-all" }}>
            {deleteTarget}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
            취소
          </Button>
          <Button
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
          >
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </AppShell>
  );
}
