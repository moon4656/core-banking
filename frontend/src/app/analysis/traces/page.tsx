"use client";

import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { GridColDef, GridRenderCellParams, GridRowParams } from "@mui/x-data-grid";
import { useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { ApiError, apiGet, apiPut } from "@/lib/api";
import { getStoredSession } from "@/lib/session";
import type {
  EvidenceItem,
  TraceEvent,
  TraceListItem,
  TraceOwnerUpdateResponse,
  TraceSummary,
} from "@/types/trace";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  try {
    const date = new Date(value.replace(" ", "T") + "Z");
    return date.toLocaleString("ko-KR");
  } catch {
    return value;
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "-";
  return value.toFixed(4);
}

function queryPreview(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 20 ? `${value.slice(0, 20)}...` : value;
}

const listColumns: GridColDef[] = [
  {
    field: "request_id",
    headerName: "Request ID",
    minWidth: 250,
    flex: 1.05,
  },
  {
    field: "query_preview",
    headerName: "질의",
    minWidth: 220,
    flex: 1.2,
    renderCell: (params: GridRenderCellParams<TraceListItem>) => (
      <Tooltip title={params.value ?? "-"}>
        <Typography variant="body2" noWrap sx={{ width: "100%" }}>
          {queryPreview(params.value as string | null | undefined)}
        </Typography>
      </Tooltip>
    ),
  },
  {
    field: "owner_name",
    headerName: "Owner",
    minWidth: 120,
    flex: 0.7,
    renderCell: (params: GridRenderCellParams<TraceListItem>) => (
      <Typography variant="body2">{(params.value as string | null | undefined) ?? "-"}</Typography>
    ),
  },
  {
    field: "last_event_type",
    headerName: "Last Event",
    minWidth: 160,
    flex: 0.85,
  },
  {
    field: "event_count",
    headerName: "Events",
    width: 88,
    align: "center",
    headerAlign: "center",
  },
  {
    field: "evidence_count",
    headerName: "Evidence",
    width: 96,
    align: "center",
    headerAlign: "center",
  },
  {
    field: "last_event_at",
    headerName: "Last At",
    minWidth: 170,
    flex: 0.8,
    renderCell: (params: GridRenderCellParams<TraceListItem>) => (
      <Typography variant="caption" color="text.secondary">
        {formatDateTime(params.value as string)}
      </Typography>
    ),
  },
];

const eventColumns: GridColDef[] = [
  { field: "event_type", headerName: "Event Type", minWidth: 180, flex: 0.9 },
  { field: "agent_id", headerName: "Agent", minWidth: 150, flex: 0.8 },
  { field: "tool_id", headerName: "Tool", minWidth: 160, flex: 0.8 },
  {
    field: "status",
    headerName: "Status",
    width: 120,
    renderCell: (params: GridRenderCellParams<TraceEvent>) => (
      <Chip
        label={String(params.value ?? "-")}
        size="small"
        color={params.value === "success" ? "success" : params.value ? "warning" : "default"}
        variant="outlined"
      />
    ),
  },
  {
    field: "duration_ms",
    headerName: "Latency",
    width: 110,
    align: "right",
    headerAlign: "right",
    renderCell: (params: GridRenderCellParams<TraceEvent>) => (
      <Typography variant="body2">{params.value != null ? `${params.value} ms` : "-"}</Typography>
    ),
  },
  {
    field: "created_at",
    headerName: "Created At",
    minWidth: 170,
    flex: 0.8,
    renderCell: (params: GridRenderCellParams<TraceEvent>) => (
      <Typography variant="caption" color="text.secondary">
        {formatDateTime(params.value as string)}
      </Typography>
    ),
  },
];

const evidenceColumns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 90 },
  { field: "concept_id", headerName: "Concept", minWidth: 180, flex: 0.9 },
  { field: "source_id", headerName: "Source", minWidth: 160, flex: 0.8 },
  {
    field: "confidence_score",
    headerName: "Confidence",
    width: 110,
    align: "right",
    headerAlign: "right",
    renderCell: (params: GridRenderCellParams<EvidenceItem>) => (
      <Typography variant="body2">{formatNumber(params.value as number | null | undefined)}</Typography>
    ),
  },
  {
    field: "data_quality_score",
    headerName: "Quality",
    width: 100,
    align: "right",
    headerAlign: "right",
    renderCell: (params: GridRenderCellParams<EvidenceItem>) => (
      <Typography variant="body2">{formatNumber(params.value as number | null | undefined)}</Typography>
    ),
  },
  {
    field: "intent_relevance_score",
    headerName: "Intent Rel.",
    width: 110,
    align: "right",
    headerAlign: "right",
    renderCell: (params: GridRenderCellParams<EvidenceItem>) => (
      <Typography variant="body2">{formatNumber(params.value as number | null | undefined)}</Typography>
    ),
  },
  {
    field: "created_at",
    headerName: "Created At",
    minWidth: 170,
    flex: 0.8,
    renderCell: (params: GridRenderCellParams<EvidenceItem>) => (
      <Typography variant="caption" color="text.secondary">
        {formatDateTime(params.value as string)}
      </Typography>
    ),
  },
];

export default function TraceAnalysisPage() {
  const [searchInput, setSearchInput] = useState("");
  const [requestIdKeyword, setRequestIdKeyword] = useState("");
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [ownerNameInput, setOwnerNameInput] = useState("");
  const [ownerRoleInput, setOwnerRoleInput] = useState("ANALYST");
  const [adminMessage, setAdminMessage] = useState<string | null>(null);

  const session = useMemo(() => getStoredSession(), []);
  const isAdmin = session?.role === "ADMIN";

  const traceListQuery = useQuery({
    queryKey: ["analysis-traces", requestIdKeyword],
    queryFn: () =>
      apiGet<TraceListItem[]>(
        `/api/v1/ai/traces${requestIdKeyword ? `?request_id=${encodeURIComponent(requestIdKeyword)}` : ""}`,
      ),
  });

  const summaryQuery = useQuery({
    queryKey: ["analysis-trace-summary", selectedRequestId],
    queryFn: () => apiGet<TraceSummary>(`/api/v1/ai/traces/${selectedRequestId}`),
    enabled: !!selectedRequestId,
  });

  const eventsQuery = useQuery({
    queryKey: ["analysis-trace-events", selectedRequestId],
    queryFn: () => apiGet<TraceEvent[]>(`/api/v1/ai/traces/${selectedRequestId}/events`),
    enabled: !!selectedRequestId,
  });

  const evidenceQuery = useQuery({
    queryKey: ["analysis-trace-evidence", selectedRequestId],
    queryFn: () => apiGet<EvidenceItem[]>(`/api/v1/ai/traces/${selectedRequestId}/evidence`),
    enabled: !!selectedRequestId,
  });

  const ownerUpdateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedRequestId) {
        throw new Error("선택된 요청이 없습니다.");
      }
      return apiPut<TraceOwnerUpdateResponse>(`/api/v1/ai/traces/${selectedRequestId}/owner`, {
        owner_name: ownerNameInput.trim(),
        owner_role: ownerRoleInput.trim() || "ANALYST",
      });
    },
    onSuccess: async (payload) => {
      setAdminMessage(`Owner를 ${payload.owner_name} (${payload.owner_role ?? "-"}) 로 변경했습니다.`);
      await Promise.all([
        traceListQuery.refetch(),
        summaryQuery.refetch(),
      ]);
    },
    onError: (error) => {
      setAdminMessage(error instanceof ApiError ? error.detail : "Owner 변경 중 오류가 발생했습니다.");
    },
  });

  const traceRows = useMemo(
    () => (traceListQuery.data ?? []).map((item) => ({ id: item.request_id, ...item })),
    [traceListQuery.data],
  );

  useEffect(() => {
    if (!traceRows.length) {
      setSelectedRequestId(null);
      return;
    }

    const exists = traceRows.some((row) => row.request_id === selectedRequestId);
    if (!selectedRequestId || !exists) {
      setSelectedRequestId(String(traceRows[0].request_id));
    }
  }, [selectedRequestId, traceRows]);

  const selectedTrace = useMemo(
    () => traceRows.find((row) => row.request_id === selectedRequestId) ?? null,
    [selectedRequestId, traceRows],
  );

  useEffect(() => {
    setOwnerNameInput(summaryQuery.data?.owner_name ?? selectedTrace?.owner_name ?? "");
    setOwnerRoleInput(summaryQuery.data?.owner_role ?? selectedTrace?.owner_role ?? "ANALYST");
    setAdminMessage(null);
  }, [selectedRequestId, selectedTrace?.owner_name, selectedTrace?.owner_role, summaryQuery.data?.owner_name, summaryQuery.data?.owner_role]);

  const listError = traceListQuery.error instanceof ApiError ? traceListQuery.error.detail : null;
  const summaryError = summaryQuery.error instanceof ApiError ? summaryQuery.error.detail : null;
  const eventsError = eventsQuery.error instanceof ApiError ? eventsQuery.error.detail : null;
  const evidenceError = evidenceQuery.error instanceof ApiError ? evidenceQuery.error.detail : null;

  return (
    <AppShell title="Trace 분석">
      <Stack spacing={2}>
        <PageCard
          title="Trace 목록 조회"
          subtitle="Request ID 검색과 최근 질의 미리보기를 함께 보면서 요청별 Trace를 확인합니다."
        >
          <Stack spacing={2}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.25}>
              <TextField
                fullWidth
                size="small"
                label="Request ID 검색"
                placeholder="request_id 일부를 입력하세요"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") setRequestIdKeyword(searchInput.trim());
                }}
              />
              <Button
                variant="contained"
                startIcon={<SearchRoundedIcon />}
                onClick={() => setRequestIdKeyword(searchInput.trim())}
                sx={{ minWidth: 120 }}
              >
                조회
              </Button>
            </Stack>

            {listError ? <Alert severity="error">{listError}</Alert> : null}

            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 340px" },
                alignItems: "start",
              }}
            >
              <BaseDataGrid
                rows={traceRows}
                columns={listColumns}
                height={440}
                onRowClick={(params: GridRowParams) => setSelectedRequestId(String(params.row.request_id))}
              />

              <PageCard
                title="요약"
                subtitle="선택한 요청의 핵심 지표와 owner 상태를 확인합니다."
              >
                {!selectedRequestId ? (
                  <Typography color="text.secondary">왼쪽에서 요청을 선택하세요.</Typography>
                ) : summaryQuery.isLoading ? (
                  <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
                    <CircularProgress size={28} />
                  </Box>
                ) : (
                  <Stack spacing={1.5}>
                    {summaryError ? <Alert severity="error">{summaryError}</Alert> : null}
                    {adminMessage ? (
                      <Alert severity={ownerUpdateMutation.isError ? "error" : "success"}>{adminMessage}</Alert>
                    ) : null}
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Request ID
                      </Typography>
                      <Typography variant="body2">{selectedRequestId}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        질의
                      </Typography>
                      <Typography variant="body2">{selectedTrace?.query_preview ?? "-"}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Owner
                      </Typography>
                      <Typography variant="body2">
                        {summaryQuery.data?.owner_name ?? "-"}
                        {summaryQuery.data?.owner_role ? ` (${summaryQuery.data.owner_role})` : ""}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Last Event
                      </Typography>
                      <Typography variant="body2">{selectedTrace?.last_event_type ?? "-"}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Event 수
                      </Typography>
                      <Typography variant="body2">{summaryQuery.data?.event_count ?? "-"}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Evidence 수
                      </Typography>
                      <Typography variant="body2">{summaryQuery.data?.evidence_count ?? "-"}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        평균 Confidence
                      </Typography>
                      <Typography variant="body2">{formatNumber(summaryQuery.data?.avg_confidence)}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        평균 Data Quality
                      </Typography>
                      <Typography variant="body2">{formatNumber(summaryQuery.data?.avg_data_quality)}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        평균 Intent Relevance
                      </Typography>
                      <Typography variant="body2">{formatNumber(summaryQuery.data?.avg_intent_relevance)}</Typography>
                    </Box>

                    {isAdmin ? (
                      <Box
                        sx={{
                          mt: 1,
                          pt: 1.5,
                          borderTop: "1px dashed",
                          borderColor: "divider",
                        }}
                      >
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>
                          Owner 수동 귀속
                        </Typography>
                        <Stack spacing={1}>
                          <TextField
                            size="small"
                            label="Owner Name"
                            value={ownerNameInput}
                            onChange={(event) => setOwnerNameInput(event.target.value)}
                            placeholder="예: legacy-user"
                          />
                          <TextField
                            size="small"
                            label="Owner Role"
                            value={ownerRoleInput}
                            onChange={(event) => setOwnerRoleInput(event.target.value)}
                            placeholder="ANALYST"
                          />
                          <Button
                            variant="contained"
                            disabled={!ownerNameInput.trim() || ownerUpdateMutation.isPending}
                            onClick={() => ownerUpdateMutation.mutate()}
                          >
                            {ownerUpdateMutation.isPending ? "저장 중..." : "Owner 저장"}
                          </Button>
                        </Stack>
                      </Box>
                    ) : null}

                    <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                      {Object.entries(summaryQuery.data?.events_by_type ?? {}).map(([eventType, count]) => (
                        <Chip key={eventType} label={`${eventType}: ${count}`} size="small" variant="outlined" />
                      ))}
                    </Stack>
                  </Stack>
                )}
              </PageCard>
            </Box>
          </Stack>
        </PageCard>

        <PageCard
          title="Trace Events"
          subtitle="단계별 이벤트, 상태, 처리 시간을 순서대로 확인합니다."
        >
          {eventsError ? <Alert severity="error">{eventsError}</Alert> : null}
          <BaseDataGrid rows={eventsQuery.data ?? []} columns={eventColumns} height={360} density="compact" />
        </PageCard>

        <PageCard
          title="Evidence"
          subtitle="응답 생성에 사용된 근거 데이터와 품질 점수를 확인합니다."
        >
          {evidenceError ? <Alert severity="error">{evidenceError}</Alert> : null}
          <BaseDataGrid rows={evidenceQuery.data ?? []} columns={evidenceColumns} height={360} density="compact" />
        </PageCard>
      </Stack>
    </AppShell>
  );
}
