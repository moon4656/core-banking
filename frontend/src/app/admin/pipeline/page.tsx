"use client";

import AutoGraphRoundedIcon from "@mui/icons-material/AutoGraphRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import HubRoundedIcon from "@mui/icons-material/HubRounded";
import RemoveCircleOutlineRoundedIcon from "@mui/icons-material/RemoveCircleOutlineRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import PsychologyAltRoundedIcon from "@mui/icons-material/PsychologyAltRounded";
import ScheduleRoundedIcon from "@mui/icons-material/ScheduleRounded";
import SourceRoundedIcon from "@mui/icons-material/SourceRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import type { GridColDef, GridRenderCellParams, GridRowParams } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { apiGet, ApiError } from "@/lib/api";
import type { TraceEvent, TraceListItem } from "@/types/trace";

type FlowStatus = "idle" | "success" | "error" | "partial";

type FlowStep = {
  id: string;
  label: string;
  description: string;
  eventTypes: string[];
};

type TraceContext = {
  userQuestion?: string;
  sessionId?: string;
  intent?: string;
  urgency?: string;
  keywords?: string[];
  directConcepts?: string[];
  expandedConcepts?: string[];
  totalConcepts?: string[];
  routedAgents?: string[];
  unroutedConcepts?: string[];
  planApiIds?: string[];
  rerankedOrder?: string[];
};

const INTENT_LABEL: Record<string, string> = {
  INQUIRY: "조회",
  COMPARISON: "비교",
  RECOMMENDATION: "추천",
  APPLICATION: "신청",
  OTHER: "기타",
};

const INTENT_COLOR: Record<string, "default" | "info" | "secondary" | "warning" | "success"> = {
  INQUIRY: "info",
  COMPARISON: "secondary",
  RECOMMENDATION: "warning",
  APPLICATION: "success",
  OTHER: "default",
};

const AGENT_LABEL: Record<string, string> = {
  PRODUCT_AGENT: "상품",
  RATE_AGENT: "금리",
  POLICY_AGENT: "정책",
  SEARCH_AGENT: "검색",
};

const FLOW_STEPS: FlowStep[] = [
  {
    id: "request",
    label: "질의 수신",
    description: "사용자 질문과 session_id를 수신합니다.",
    eventTypes: ["REQUEST_RECEIVED"],
  },
  {
    id: "memory",
    label: "Memory 로드",
    description: "Short / Long-term memory를 불러옵니다.",
    eventTypes: ["MEMORY_LOADED", "LTM_LOADED"],
  },
  {
    id: "intent",
    label: "Intent 분석",
    description: "의도, 키워드, 긴급도를 분석합니다.",
    eventTypes: ["INTENT_ANALYZED"],
  },
  {
    id: "concept",
    label: "Concept 탐지",
    description: "질문과 관계 확장을 통해 Concept를 추출합니다.",
    eventTypes: ["CONCEPT_DETECTED"],
  },
  {
    id: "agent",
    label: "Agent 선택",
    description: "agent_concept_mapping 기반으로 실행 Agent를 결정합니다.",
    eventTypes: ["AGENT_SELECTED"],
  },
  {
    id: "plan",
    label: "실행 계획",
    description: "호출할 API/Tool 계획을 구성합니다.",
    eventTypes: ["PLAN_CREATED"],
  },
  {
    id: "tool",
    label: "Tool 실행",
    description: "선택된 Agent가 Tool을 호출해 근거를 수집합니다.",
    eventTypes: ["TOOL_INVOKED"],
  },
  {
    id: "rerank",
    label: "Re-ranking",
    description: "근거와 성공 결과를 재정렬합니다.",
    eventTypes: ["RESULTS_RERANKED"],
  },
  {
    id: "response",
    label: "응답 완료",
    description: "최종 답변을 생성하고 클라이언트에 반환합니다.",
    eventTypes: ["RESPONSE_COMPLETED"],
  },
];

const STATUS_STYLE: Record<FlowStatus, { bg: string; border: string; text: string; line: string }> = {
  idle: { bg: "#f8fafc", border: "#e2e8f0", text: "#94a3b8", line: "#e2e8f0" },
  success: { bg: "#f0fdf4", border: "#86efac", text: "#166534", line: "#86efac" },
  error: { bg: "#fef2f2", border: "#fca5a5", text: "#b91c1c", line: "#fca5a5" },
  partial: { bg: "#fffbeb", border: "#fcd34d", text: "#b45309", line: "#fcd34d" },
};

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  try {
    const date = new Date(value.replace(" ", "T") + "Z");
    return date.toLocaleString("ko-KR");
  } catch {
    return value;
  }
}

function shortenQuestion(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 20 ? `${value.slice(0, 20)}...` : value;
}

function extractContext(events: TraceEvent[]): TraceContext {
  const byType = new Map<string, TraceEvent>();
  for (const event of events) {
    if (!byType.has(event.event_type)) byType.set(event.event_type, event);
  }

  const request = byType.get("REQUEST_RECEIVED");
  const intent = byType.get("INTENT_ANALYZED");
  const concept = byType.get("CONCEPT_DETECTED");
  const agent = byType.get("AGENT_SELECTED");
  const plan = byType.get("PLAN_CREATED");
  const rerank = byType.get("RESULTS_RERANKED");

  return {
    userQuestion: request?.input_data?.message as string | undefined,
    sessionId: request?.input_data?.session_id as string | undefined,
    intent: intent?.output_data?.intent as string | undefined,
    urgency: intent?.output_data?.urgency as string | undefined,
    keywords: intent?.output_data?.keywords as string[] | undefined,
    directConcepts: concept?.output_data?.detected_concepts as string[] | undefined,
    expandedConcepts: concept?.output_data?.expanded_concepts as string[] | undefined,
    totalConcepts: concept?.output_data?.total_concepts as string[] | undefined,
    routedAgents: agent?.output_data?.routed_agents as string[] | undefined,
    unroutedConcepts: agent?.output_data?.unrouted_concepts as string[] | undefined,
    planApiIds: plan?.output_data?.api_ids as string[] | undefined,
    rerankedOrder: rerank?.output_data?.ranked_order as string[] | undefined,
  };
}

function getStepEvents(events: TraceEvent[], step: FlowStep): TraceEvent[] {
  return events.filter((event) => step.eventTypes.includes(event.event_type));
}

function getStepStatus(stepEvents: TraceEvent[]): FlowStatus {
  if (stepEvents.length === 0) return "idle";
  const hasError = stepEvents.some((event) => ["error", "failed"].includes(event.status));
  const hasSuccess = stepEvents.some((event) => event.status === "success");
  if (hasError && hasSuccess) return "partial";
  if (hasError) return "error";
  return "success";
}

function getStepDuration(stepEvents: TraceEvent[]): number | null {
  const durations = stepEvents.map((event) => event.duration_ms).filter((value): value is number => value != null);
  if (!durations.length) return null;
  return durations.reduce((sum, value) => sum + value, 0);
}

function StatusIcon({ status }: { status: FlowStatus }) {
  if (status === "success") return <CheckCircleRoundedIcon sx={{ fontSize: 18, color: "#16a34a" }} />;
  if (status === "error") return <ErrorRoundedIcon sx={{ fontSize: 18, color: "#dc2626" }} />;
  if (status === "partial") return <WarningAmberRoundedIcon sx={{ fontSize: 18, color: "#d97706" }} />;
  return <RemoveCircleOutlineRoundedIcon sx={{ fontSize: 18, color: "#94a3b8" }} />;
}

function MiniChip({
  label,
  color = "default",
  tooltip,
}: {
  label: string;
  color?: "default" | "primary" | "secondary" | "info" | "warning" | "success" | "error";
  tooltip?: string;
}) {
  const chip = (
    <Chip
      label={label}
      size="small"
      color={color}
      variant="outlined"
      sx={{ height: 22, fontSize: 11 }}
    />
  );

  return tooltip ? <Tooltip title={tooltip}>{chip}</Tooltip> : chip;
}

function FlowNode({
  index,
  step,
  events,
  context,
}: {
  index: number;
  step: FlowStep;
  events: TraceEvent[];
  context: TraceContext;
}) {
  const stepEvents = getStepEvents(events, step);
  const status = getStepStatus(stepEvents);
  const duration = getStepDuration(stepEvents);
  const style = STATUS_STYLE[status];

  return (
    <Stack spacing={0}>
      {index > 0 ? (
        <Box sx={{ display: "flex", justifyContent: "center" }}>
          <Box sx={{ width: 2, height: 20, backgroundColor: style.line }} />
        </Box>
      ) : null}

      <Paper
        elevation={0}
        sx={{
          p: 1.75,
          borderRadius: 3,
          border: "1px solid",
          borderColor: style.border,
          backgroundColor: style.bg,
        }}
      >
        <Stack direction="row" spacing={1.25} alignItems="flex-start">
          <Chip
            label={index + 1}
            size="small"
            sx={{
              mt: 0.1,
              width: 28,
              height: 22,
              fontSize: 11,
              fontWeight: 700,
              border: "1px solid",
              borderColor: style.border,
              color: style.text,
              backgroundColor: "rgba(255,255,255,0.72)",
            }}
          />
          <StatusIcon status={status} />
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap" sx={{ mb: 0.5 }}>
              <Typography variant="subtitle2" fontWeight={700}>
                {step.label}
              </Typography>
              {duration != null ? (
                <Chip label={`${duration} ms`} size="small" variant="outlined" sx={{ height: 20, fontSize: 10 }} />
              ) : null}
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {step.description}
            </Typography>

            <Stack direction="row" spacing={0.6} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
              {step.id === "request" && context.userQuestion ? (
                <MiniChip label={shortenQuestion(context.userQuestion)} tooltip={context.userQuestion} color="info" />
              ) : null}
              {step.id === "memory" && context.sessionId ? (
                <MiniChip label={`session ${context.sessionId}`} tooltip={context.sessionId} />
              ) : null}
              {step.id === "intent" && context.intent ? (
                <>
                  <MiniChip
                    label={INTENT_LABEL[context.intent] ?? context.intent}
                    color={INTENT_COLOR[context.intent] ?? "default"}
                  />
                  {context.urgency ? <MiniChip label={`긴급도 ${context.urgency}`} color="warning" /> : null}
                </>
              ) : null}
              {step.id === "concept" && context.totalConcepts?.length ? (
                <>
                  <MiniChip label={`총 Concept ${context.totalConcepts.length}`} color="primary" />
                  {context.directConcepts?.slice(0, 3).map((concept) => (
                    <MiniChip key={concept} label={concept.replace("CONCEPT_", "")} tooltip={concept} />
                  ))}
                </>
              ) : null}
              {step.id === "agent" && context.routedAgents?.length ? (
                <>
                  <MiniChip label={`선택 Agent ${context.routedAgents.length}`} color="secondary" />
                  {context.routedAgents.map((agent) => (
                    <MiniChip key={agent} label={AGENT_LABEL[agent] ?? agent} tooltip={agent} />
                  ))}
                </>
              ) : null}
              {step.id === "plan" && context.planApiIds?.length ? (
                <>
                  <MiniChip label={`API ${context.planApiIds.length}`} color="info" />
                  {context.planApiIds.slice(0, 4).map((apiId) => (
                    <MiniChip key={apiId} label={apiId.replace("MOCK_", "")} tooltip={apiId} />
                  ))}
                </>
              ) : null}
              {step.id === "tool" ? (
                <>
                  <MiniChip label={`호출 ${stepEvents.length}건`} color="success" />
                  {stepEvents.slice(0, 4).map((event) => (
                    <MiniChip
                      key={`${event.id}-${event.tool_id}`}
                      label={String(event.tool_id ?? "UNKNOWN").replace("MOCK_", "")}
                      tooltip={String(event.tool_id ?? "")}
                      color={event.status === "success" ? "success" : "error"}
                    />
                  ))}
                </>
              ) : null}
              {step.id === "rerank" && context.rerankedOrder?.length ? (
                <>
                  <MiniChip label={`후보 ${context.rerankedOrder.length}건`} color="warning" />
                  {context.rerankedOrder.slice(0, 3).map((item, itemIndex) => (
                    <MiniChip key={`${item}-${itemIndex}`} label={`${itemIndex + 1}. ${item.replace("MOCK_", "")}`} />
                  ))}
                </>
              ) : null}
              {step.id === "response" && stepEvents.length ? (
                <MiniChip label="최종 응답 반환" color="success" />
              ) : null}
            </Stack>
          </Box>
        </Stack>
      </Paper>
    </Stack>
  );
}

function buildColumns(): GridColDef[] {
  return [
    {
      field: "query_preview",
      headerName: "질의",
      flex: 1.4,
      minWidth: 170,
      renderCell: (params: GridRenderCellParams<TraceListItem>) => (
        <Tooltip title={params.value ?? "-"}>
          <Typography variant="body2" noWrap sx={{ width: "100%" }}>
            {params.value ?? "-"}
          </Typography>
        </Tooltip>
      ),
    },
    {
      field: "intent",
      headerName: "Intent",
      width: 90,
      renderCell: (params: GridRenderCellParams<TraceListItem>) =>
        params.value ? (
          <Chip
            label={INTENT_LABEL[String(params.value)] ?? String(params.value)}
            size="small"
            color={INTENT_COLOR[String(params.value)] ?? "default"}
            variant="outlined"
            sx={{ fontSize: 10 }}
          />
        ) : (
          <Typography variant="caption" color="text.disabled">
            -
          </Typography>
        ),
    },
    {
      field: "selected_agents_count",
      headerName: "Agent",
      width: 72,
      align: "center",
      headerAlign: "center",
    },
    {
      field: "event_count",
      headerName: "Events",
      width: 72,
      align: "center",
      headerAlign: "center",
    },
    {
      field: "last_event_at",
      headerName: "최근",
      width: 140,
      renderCell: (params: GridRenderCellParams<TraceListItem>) => (
        <Typography variant="caption" color="text.secondary">
          {formatDateTime(params.value as string)}
        </Typography>
      ),
    },
  ];
}

export default function PipelineFlowPage() {
  const [searchInput, setSearchInput] = useState("");
  const [requestIdKeyword, setRequestIdKeyword] = useState("");
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  const traceListQuery = useQuery({
    queryKey: ["pipeline-trace-list", requestIdKeyword],
    queryFn: () =>
      apiGet<TraceListItem[]>(
        `/api/v1/ai/traces${requestIdKeyword ? `?request_id=${encodeURIComponent(requestIdKeyword)}` : ""}`,
      ),
  });

  const eventsQuery = useQuery({
    queryKey: ["pipeline-events", selectedRequestId],
    queryFn: () => apiGet<TraceEvent[]>(`/api/v1/ai/traces/${selectedRequestId}/events`),
    enabled: !!selectedRequestId,
  });

  const traceRows = useMemo(
    () => (traceListQuery.data ?? []).map((item) => ({ id: item.request_id, ...item })),
    [traceListQuery.data],
  );

  useEffect(() => {
    if (!selectedRequestId && traceRows.length > 0) {
      setSelectedRequestId(String(traceRows[0].request_id));
    }
  }, [selectedRequestId, traceRows]);

  const events = useMemo(() => eventsQuery.data ?? [], [eventsQuery.data]);
  const context = useMemo(() => extractContext(events), [events]);
  const totalLatency = useMemo(
    () => events.reduce((sum, event) => sum + (event.duration_ms ?? 0), 0),
    [events],
  );
  const toolEvents = useMemo(
    () => events.filter((event) => event.event_type === "TOOL_INVOKED"),
    [events],
  );
  const toolSuccess = toolEvents.filter((event) => event.status === "success").length;

  const listError =
    traceListQuery.error instanceof ApiError ? traceListQuery.error.detail : null;
  const eventsError =
    eventsQuery.error instanceof ApiError ? eventsQuery.error.detail : null;

  return (
    <AppShell title="파이프라인 플로우">
      <Stack spacing={2}>
        <PageCard
          title="Pipeline Explorer"
          subtitle="좌측에서 요청 내역을 고르고, 우측에서 실행 흐름과 단계별 결과를 확인합니다."
        >
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", xl: "400px minmax(0, 1fr)" },
              alignItems: "start",
              minHeight: { xl: "calc(100vh - 220px)" },
            }}
          >
            <Stack spacing={1.5}>
              <Stack direction={{ xs: "column", sm: "row", xl: "column" }} spacing={1.25}>
                <TextField
                  fullWidth
                  size="small"
                  label="Request ID 검색"
                  placeholder="request_id 일부 입력"
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
                  sx={{ flexShrink: 0 }}
                >
                  조회
                </Button>
              </Stack>

              {listError ? <Alert severity="error">{listError}</Alert> : null}

              <BaseDataGrid
                rows={traceRows}
                columns={buildColumns()}
                height={640}
                density="compact"
                onRowClick={(params: GridRowParams) => setSelectedRequestId(String(params.row.request_id))}
                rowSelectionModel={selectedRequestId ? [selectedRequestId] : []}
              />
            </Stack>

            <Stack spacing={2} sx={{ minHeight: 0 }}>
              <PageCard
                title={
                  selectedRequestId
                    ? `실행 흐름 - ${selectedRequestId.slice(-12)}`
                    : "실행 흐름"
                }
                subtitle="요약 정보와 단계별 파이프라인 상태를 한 화면에서 확인합니다."
              >
                {eventsError ? <Alert severity="error">{eventsError}</Alert> : null}

                {!selectedRequestId ? (
                  <Typography color="text.secondary">좌측에서 요청을 선택해주세요.</Typography>
                ) : eventsQuery.isLoading ? (
                  <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Stack spacing={2}>
                    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                      {context.userQuestion ? (
                        <Chip
                          icon={<SourceRoundedIcon />}
                          label={shortenQuestion(context.userQuestion)}
                          variant="outlined"
                        />
                      ) : null}
                      {context.intent ? (
                        <Chip
                          icon={<PsychologyAltRoundedIcon />}
                          label={INTENT_LABEL[context.intent] ?? context.intent}
                          color={INTENT_COLOR[context.intent] ?? "default"}
                          variant="outlined"
                        />
                      ) : null}
                      <Chip
                        icon={<HubRoundedIcon />}
                        label={`Agent ${context.routedAgents?.length ?? 0}`}
                        variant="outlined"
                      />
                      <Chip
                        icon={<AutoGraphRoundedIcon />}
                        label={`Concept ${context.totalConcepts?.length ?? 0}`}
                        variant="outlined"
                      />
                      <Chip
                        icon={<ScheduleRoundedIcon />}
                        label={`총 ${totalLatency.toLocaleString()} ms`}
                        color="success"
                        variant="outlined"
                      />
                      <Chip
                        label={`Tool ${toolSuccess}/${toolEvents.length} 성공`}
                        color={toolSuccess === toolEvents.length ? "success" : "warning"}
                        variant="outlined"
                      />
                    </Stack>

                    <Box
                      sx={{
                        display: "grid",
                        gap: 1.5,
                        gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" },
                      }}
                    >
                      <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          질의
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                          {context.userQuestion ?? "-"}
                        </Typography>
                      </Paper>
                      <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          키워드
                        </Typography>
                        <Typography variant="body2">
                          {context.keywords?.join(", ") || "-"}
                        </Typography>
                      </Paper>
                      <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          최근 이벤트
                        </Typography>
                        <Typography variant="body2">
                          {events.length ? formatDateTime(events[events.length - 1]?.created_at) : "-"}
                        </Typography>
                      </Paper>
                    </Box>

                    <Divider />

                    <Box
                      sx={{
                        minHeight: 0,
                        maxHeight: { xs: "none", xl: "calc(100vh - 470px)" },
                        overflowY: { xs: "visible", xl: "auto" },
                        pr: { xl: 1 },
                      }}
                    >
                      <Stack spacing={0}>
                        {FLOW_STEPS.map((step, index) => (
                          <FlowNode
                            key={step.id}
                            index={index}
                            step={step}
                            events={events}
                            context={context}
                          />
                        ))}
                      </Stack>
                    </Box>
                  </Stack>
                )}
              </PageCard>
            </Stack>
          </Box>
        </PageCard>
      </Stack>
    </AppShell>
  );
}
