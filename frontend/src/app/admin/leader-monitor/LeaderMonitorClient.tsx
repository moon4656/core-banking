"use client";

import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import MonitorRoundedIcon from "@mui/icons-material/MonitorRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import BlockRoundedIcon from "@mui/icons-material/BlockRounded";
import HourglassEmptyRoundedIcon from "@mui/icons-material/HourglassEmptyRounded";
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import {
  fetchMonTraceDetail,
  fetchMonTraces,
  MonGateDetail,
  MonTraceDetailResponse,
  MonTraceListItem,
} from "@/lib/api";

// ─────────────────────────────────────────────────────────────
// 상수 & 헬퍼
// ─────────────────────────────────────────────────────────────

// 목록 필터 — status 값은 백엔드 소문자 그대로
const STATUS_FILTERS = [
  { value: "", label: "전체" },
  { value: "completed", label: "완료" },
  { value: "warning", label: "경고" },
  { value: "blocked", label: "차단" },
  { value: "processing", label: "진행중" },
] as const;

const INTENT_LABEL: Record<string, string> = {
  INQUIRY: "조회",
  COMPARISON: "비교",
  RECOMMENDATION: "추천",
  APPLICATION: "신청",
  OTHER: "기타",
};

// 트레이스 status(소문자) → MUI color
function traceStatusColor(s: string): "success" | "warning" | "error" | "info" | "default" {
  if (s === "completed") return "success";
  if (s === "warning") return "warning";
  if (s === "blocked") return "error";
  if (s === "processing") return "info";
  return "default";
}

// Gate result(대문자) → MUI color
function gateResultColor(r: string | null): "success" | "warning" | "error" | "default" {
  if (r === "PASS") return "success";
  if (r === "WARNING") return "warning";
  if (r === "BLOCKED") return "error";
  return "default";
}

// 트레이스 status → 아이콘
function TraceStatusIcon({ status, size = 15 }: { status: string; size?: number }) {
  const sx = { fontSize: size };
  if (status === "completed") return <CheckCircleRoundedIcon sx={{ ...sx, color: "success.main" }} />;
  if (status === "warning") return <WarningAmberRoundedIcon sx={{ ...sx, color: "warning.main" }} />;
  if (status === "blocked") return <ErrorRoundedIcon sx={{ ...sx, color: "error.main" }} />;
  if (status === "processing") return <HourglassEmptyRoundedIcon sx={{ ...sx, color: "info.main" }} />;
  return <BlockRoundedIcon sx={{ ...sx, color: "text.disabled" }} />;
}

// Gate result → 아이콘
function GateResultIcon({ result, size = 14 }: { result: string | null; size?: number }) {
  const sx = { fontSize: size };
  if (result === "PASS") return <CheckCircleRoundedIcon sx={{ ...sx, color: "success.main" }} />;
  if (result === "WARNING") return <WarningAmberRoundedIcon sx={{ ...sx, color: "warning.main" }} />;
  if (result === "BLOCKED") return <ErrorRoundedIcon sx={{ ...sx, color: "error.main" }} />;
  return <BlockRoundedIcon sx={{ ...sx, color: "text.disabled" }} />;
}

function fmtTime(iso: string | null | undefined) {
  if (!iso) return "-";
  const date = new Date(iso);
  const displayTimeZone = process.env.NEXT_PUBLIC_APP_TIMEZONE || "Asia/Seoul";
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: displayTimeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day} ${values.hour}:${values.minute}:${values.second}`;
}

function queryLabel(item: MonTraceListItem) {
  const prefix = item.user_id ? `${item.user_id} 요청: ` : "";
  return item.original_query ? prefix + item.original_query : "(쿼리 없음)";
}

// ─────────────────────────────────────────────────────────────
// Gate Bar
// ─────────────────────────────────────────────────────────────

function GateBar({ gates }: { gates: MonGateDetail[] }) {
  if (!gates.length) return null;
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
      {gates.map((g, i) => (
        <Chip
          key={i}
          icon={<GateResultIcon result={g.result} />}
          label={g.gate_name ?? g.gate_type ?? `Gate ${i + 1}`}
          size="small"
          color={gateResultColor(g.result)}
          variant="outlined"
          title={g.message ?? undefined}
          sx={{ fontSize: 11 }}
        />
      ))}
    </Stack>
  );
}

// ─────────────────────────────────────────────────────────────
// 탭 패널들
// ─────────────────────────────────────────────────────────────

function IntentTab({ detail }: { detail: MonTraceDetailResponse }) {
  const d = detail.intent;
  if (!d) return <Typography variant="caption" color="text.disabled">데이터 없음</Typography>;
  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
        <Box>
          <Typography variant="caption" color="text.secondary">주요 의도</Typography>
          <Typography variant="body2" fontWeight={600}>
            {d.primary_intent ? (INTENT_LABEL[d.primary_intent] ?? d.primary_intent) : "-"}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">신뢰도</Typography>
          <Typography variant="body2" fontWeight={600}>
            {d.confidence != null ? `${(d.confidence * 100).toFixed(0)}%` : "-"}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">쿼리 유형</Typography>
          <Typography variant="body2" fontWeight={600}>{d.query_type ?? "-"}</Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">Tool 필요</Typography>
          <Typography variant="body2" fontWeight={600}>{d.needs_tool_execution ? "예" : "아니오"}</Typography>
        </Box>
      </Stack>
      {d.secondary_intents?.length > 0 && (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>보조 의도</Typography>
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            {d.secondary_intents.map((s) => (
              <Chip key={s} label={s} size="small" variant="outlined" sx={{ fontSize: 11 }} />
            ))}
          </Stack>
        </Box>
      )}
      {d.reason && (
        <Box>
          <Typography variant="caption" color="text.secondary">분석 근거</Typography>
          <Typography variant="body2" sx={{ mt: 0.25 }}>{d.reason}</Typography>
        </Box>
      )}
    </Stack>
  );
}

function ConceptTab({ detail }: { detail: MonTraceDetailResponse }) {
  const gate1 = detail.gates.find((g) => g.gate_name === "concept_confidence");
  return (
    <Stack spacing={1.5}>
      {gate1 && (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Stack direction="row" alignItems="center" spacing={0.75}>
            <GateResultIcon result={gate1.result} />
            <Typography variant="caption" fontWeight={600}>{gate1.gate_name}</Typography>
            {gate1.message && (
              <Typography variant="caption" color="text.secondary">— {gate1.message}</Typography>
            )}
            <Chip label={gate1.result ?? "-"} size="small" color={gateResultColor(gate1.result)} sx={{ fontSize: 10, height: 18, ml: "auto" }} />
          </Stack>
        </Paper>
      )}
      {detail.concepts.length === 0 ? (
        <Typography variant="caption" color="text.disabled">탐지된 Concept 없음</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontSize: 12 }}>Concept ID</TableCell>
              <TableCell sx={{ fontSize: 12 }}>레이블</TableCell>
              <TableCell sx={{ fontSize: 12 }}>신뢰도</TableCell>
              <TableCell sx={{ fontSize: 12 }}>상태</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {detail.concepts.map((c, i) => (
              <TableRow key={i} hover>
                <TableCell sx={{ fontSize: 11, fontFamily: "monospace" }}>{c.concept_id ?? "-"}</TableCell>
                <TableCell sx={{ fontSize: 12 }}>{c.concept_label ?? "-"}</TableCell>
                <TableCell sx={{ fontSize: 12, minWidth: 120 }}>
                  {c.confidence != null ? (
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <LinearProgress
                        variant="determinate"
                        value={c.confidence * 100}
                        sx={{ flex: 1, height: 6, borderRadius: 3 }}
                        color={c.confidence >= 0.7 ? "success" : "warning"}
                      />
                      <Typography variant="caption">{(c.confidence * 100).toFixed(0)}%</Typography>
                    </Stack>
                  ) : "-"}
                </TableCell>
                <TableCell>
                  {c.status && (
                    <Chip label={c.status} size="small" sx={{ fontSize: 10, height: 18 }} />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Stack>
  );
}

function RoutingTab({ detail }: { detail: MonTraceDetailResponse }) {
  const gate2 = detail.gates.find((g) => g.gate_name === "agent_routing");
  const selected = detail.routing.filter((r) => r.selected).sort((a, b) => (a.execution_order ?? 99) - (b.execution_order ?? 99));
  const excluded = detail.routing.filter((r) => !r.selected);
  return (
    <Stack spacing={1.5}>
      {gate2 && (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Stack direction="row" alignItems="center" spacing={0.75}>
            <GateResultIcon result={gate2.result} />
            <Typography variant="caption" fontWeight={600}>{gate2.gate_name}</Typography>
            {gate2.message && (
              <Typography variant="caption" color="text.secondary">— {gate2.message}</Typography>
            )}
            <Chip label={gate2.result ?? "-"} size="small" color={gateResultColor(gate2.result)} sx={{ fontSize: 10, height: 18, ml: "auto" }} />
          </Stack>
        </Paper>
      )}
      <Typography variant="caption" fontWeight={600} color="text.secondary">선택된 Agent ({selected.length})</Typography>
      {selected.length === 0 ? (
        <Typography variant="caption" color="text.disabled">없음</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontSize: 12 }}>순서</TableCell>
              <TableCell sx={{ fontSize: 12 }}>Agent</TableCell>
              <TableCell sx={{ fontSize: 12 }}>이유</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {selected.map((r, i) => (
              <TableRow key={i} hover>
                <TableCell sx={{ fontSize: 12 }}>#{r.execution_order ?? "-"}</TableCell>
                <TableCell sx={{ fontSize: 12, fontWeight: 600 }}>{r.agent_name}</TableCell>
                <TableCell sx={{ fontSize: 12, color: "text.secondary" }}>{r.reason ?? "-"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {excluded.length > 0 && (
        <>
          <Typography variant="caption" fontWeight={600} color="text.secondary">제외된 Agent ({excluded.length})</Typography>
          <Table size="small">
            <TableBody>
              {excluded.map((r, i) => (
                <TableRow key={i} hover>
                  <TableCell sx={{ fontSize: 12, color: "text.disabled" }}>{r.agent_name}</TableCell>
                  <TableCell sx={{ fontSize: 12, color: "text.secondary" }}>{r.reason ?? "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </Stack>
  );
}

function ToolTab({ detail }: { detail: MonTraceDetailResponse }) {
  if (!detail.tools.length) return <Typography variant="caption" color="text.disabled">Tool 실행 없음</Typography>;
  return (
    <Stack spacing={1.5}>
      {detail.tools.map((t, i) => (
        <Paper key={i} variant="outlined" sx={{ p: 1.5 }}>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <Typography variant="body2" fontWeight={600}>{t.tool_name ?? "-"}</Typography>
            {t.agent_name && <Chip label={t.agent_name} size="small" sx={{ fontSize: 10, height: 18 }} />}
            {t.latency_ms != null && (
              <Typography variant="caption" color="text.secondary">{t.latency_ms}ms</Typography>
            )}
            <Box sx={{ flex: 1 }} />
            {t.status && (
              <Chip
                label={t.status}
                size="small"
                color={t.status === "success" ? "success" : t.error_message ? "error" : "default"}
                sx={{ fontSize: 10, height: 18 }}
              />
            )}
          </Stack>
          {t.tool_input && (
            <Box
              component="pre"
              sx={{
                m: 0, mb: 0.75, p: 1, borderRadius: 1,
                bgcolor: "action.hover",
                fontSize: 11, fontFamily: "monospace",
                overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all",
              }}
            >
              {JSON.stringify(t.tool_input, null, 2)}
            </Box>
          )}
          {t.output_summary && (
            <Typography variant="caption" color="text.secondary">{t.output_summary}</Typography>
          )}
          {t.error_message && (
            <Typography variant="caption" color="error.main" display="block" sx={{ mt: 0.5 }}>{t.error_message}</Typography>
          )}
        </Paper>
      ))}
    </Stack>
  );
}

function AnswerTab({ detail }: { detail: MonTraceDetailResponse }) {
  const gate3 = detail.gates.find((g) => g.gate_name === "answer_grounding");
  if (!detail.sentences.length && !gate3) return <Typography variant="caption" color="text.disabled">데이터 없음</Typography>;
  const groundedCount = detail.sentences.filter((s) => s.grounded).length;
  return (
    <Stack spacing={1.5}>
      {gate3 && (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Stack direction="row" alignItems="center" spacing={0.75}>
            <GateResultIcon result={gate3.result} />
            <Typography variant="caption" fontWeight={600}>{gate3.gate_name}</Typography>
            {gate3.message && (
              <Typography variant="caption" color="text.secondary">— {gate3.message}</Typography>
            )}
            <Chip label={gate3.result ?? "-"} size="small" color={gateResultColor(gate3.result)} sx={{ fontSize: 10, height: 18, ml: "auto" }} />
          </Stack>
        </Paper>
      )}
      {detail.sentences.length > 0 && (
        <Typography variant="caption" color="text.secondary">
          답변 문장 분석 — {detail.sentences.length}개 문장, 근거 없음 {detail.sentences.length - groundedCount}개
        </Typography>
      )}
      {detail.sentences.map((s, i) => (
        <Paper
          key={i}
          variant="outlined"
          sx={{
            p: 1.25,
            borderColor: s.grounded ? "success.light" : "error.light",
            borderLeftWidth: 3,
          }}
        >
          <Stack direction="row" alignItems="flex-start" spacing={0.75}>
            {s.grounded
              ? <CheckCircleRoundedIcon sx={{ fontSize: 14, color: "success.main", mt: 0.2, flexShrink: 0 }} />
              : <ErrorRoundedIcon sx={{ fontSize: 14, color: "error.main", mt: 0.2, flexShrink: 0 }} />
            }
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" sx={{ mb: 0.5 }}>{s.answer_sentence ?? "-"}</Typography>
              {s.grounded && (
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                  {s.source_agent && <Chip label={s.source_agent} size="small" sx={{ fontSize: 10, height: 17 }} />}
                  {s.source_tool && <Chip label={s.source_tool} size="small" variant="outlined" color="secondary" sx={{ fontSize: 10, height: 17 }} />}
                  {s.evidence_summary && (
                    <Typography variant="caption" color="success.main">근거: {s.evidence_summary}</Typography>
                  )}
                </Stack>
              )}
              {!s.grounded && s.warning_message && (
                <Typography variant="caption" color="error.main">{s.warning_message}</Typography>
              )}
            </Box>
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

// ─────────────────────────────────────────────────────────────
// 트레이스 목록 아이템
// ─────────────────────────────────────────────────────────────

function TraceListRow({
  item,
  selected,
  onClick,
}: {
  item: MonTraceListItem;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <Box
      onClick={onClick}
      sx={{
        px: 1.5, py: 1.25,
        cursor: "pointer",
        borderRadius: 1,
        bgcolor: selected ? "action.selected" : "transparent",
        borderLeft: "3px solid",
        borderColor: selected ? "primary.main" : "transparent",
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Stack direction="row" alignItems="center" spacing={0.75} sx={{ mb: 0.35 }}>
        <TraceStatusIcon status={item.status} />
        <Chip
          label={item.status}
          size="small"
          color={traceStatusColor(item.status)}
          sx={{ fontSize: 10, height: 16 }}
        />
        {item.total_latency_ms != null && (
          <Typography variant="caption" color="text.disabled" sx={{ ml: "auto" }}>
            {item.total_latency_ms}ms
          </Typography>
        )}
      </Stack>
      <Typography
        variant="body2"
        sx={{
          fontSize: 12, lineHeight: 1.4,
          overflow: "hidden", textOverflow: "ellipsis",
          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
        }}
      >
        {queryLabel(item)}
      </Typography>
      <Typography variant="caption" color="text.disabled">{fmtTime(item.created_at)}</Typography>
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────
// 메인 컴포넌트
// ─────────────────────────────────────────────────────────────

export function LeaderMonitorClient() {
  const [statusFilter, setStatusFilter] = useState("");
  const [traces, setTraces] = useState<MonTraceListItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<MonTraceDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadList = useCallback(async () => {
    setListLoading(true);
    try {
      const res = await fetchMonTraces(1, 50, statusFilter || undefined);
      setTraces(res.items);
    } catch {
      // ignore
    } finally {
      setListLoading(false);
    }
  }, [statusFilter]);

  const loadDetail = useCallback(async (requestId: string) => {
    setDetailLoading(true);
    setDetail(null);
    try {
      const res = await fetchMonTraceDetail(requestId);
      setDetail(res);
    } catch {
      // ignore
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
    intervalRef.current = setInterval(() => void loadList(), 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [loadList]);

  useEffect(() => {
    if (traces.length === 0) {
      setSelectedId(null);
      setDetail(null);
      return;
    }

    const currentExists = selectedId
      ? traces.some((trace) => trace.request_id === selectedId)
      : false;
    const nextSelectedId = currentExists ? selectedId : traces[0].request_id;

    if (!nextSelectedId) {
      return;
    }

    if (nextSelectedId !== selectedId) {
      setSelectedId(nextSelectedId);
      setActiveTab(0);
      void loadDetail(nextSelectedId);
    }
  }, [loadDetail, selectedId, traces]);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    setActiveTab(0);
    void loadDetail(id);
  };

  const headerWarningSummary = detail
    ? detail.gates
      .filter((gate) => (gate.result === "WARNING" || gate.result === "BLOCKED") && gate.message)
      .map((gate) => gate.message?.trim())
      .find((message): message is string => Boolean(message))
    : null;

  return (
    <AppShell title="파이프라인 모니터">
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <MonitorRoundedIcon color="primary" />
        <Typography variant="h6" fontWeight={700}>Leader Agent 파이프라인 모니터</Typography>
        <Box sx={{ flex: 1 }} />
        <Tooltip title="새로고침">
          <IconButton size="small" onClick={() => void loadList()} disabled={listLoading}>
            {listLoading ? <CircularProgress size={16} /> : <RefreshRoundedIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
      </Stack>

      <Stack
        direction={{ xs: "column", lg: "row" }}
        spacing={2}
        sx={{ flex: 1, minHeight: 0, height: "calc(100vh - 160px)" }}
      >
        {/* 왼쪽: 트레이스 목록 */}
        <Paper
          variant="outlined"
          sx={{ width: { lg: 300 }, flexShrink: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}
        >
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ p: 1, borderBottom: "1px solid", borderColor: "divider" }}>
            {STATUS_FILTERS.map((f) => (
              <Chip
                key={f.value}
                label={f.label}
                size="small"
                variant={statusFilter === f.value ? "filled" : "outlined"}
                color={statusFilter === f.value ? "primary" : "default"}
                onClick={() => setStatusFilter(f.value)}
                sx={{ cursor: "pointer", fontSize: 11 }}
              />
            ))}
          </Stack>
          <Box sx={{ flex: 1, overflowY: "auto" }}>
            {traces.length === 0 ? (
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: 120 }}>
                <Typography variant="caption" color="text.disabled">
                  {listLoading ? "로딩 중…" : "데이터 없음"}
                </Typography>
              </Box>
            ) : (
              <Stack divider={<Divider />}>
                {traces.map((t) => (
                  <TraceListRow
                    key={t.request_id}
                    item={t}
                    selected={selectedId === t.request_id}
                    onClick={() => handleSelect(t.request_id)}
                  />
                ))}
              </Stack>
            )}
          </Box>
        </Paper>

        {/* 오른쪽: 상세 */}
        <Paper
          variant="outlined"
          sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}
        >
          {!selectedId ? (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", flexDirection: "column", gap: 1 }}>
              <MonitorRoundedIcon sx={{ fontSize: 40, color: "text.disabled" }} />
              <Typography variant="body2" color="text.disabled">목록에서 요청을 선택하세요</Typography>
            </Box>
          ) : detailLoading ? (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <CircularProgress size={32} />
            </Box>
          ) : detail ? (
            <>
              {/* 상세 헤더 */}
              <Box sx={{ px: 2, pt: 1.75, pb: 1, borderBottom: "1px solid", borderColor: "divider" }}>
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.75 }}>
                  <TraceStatusIcon status={detail.trace.status} />
                  <Chip
                    label={detail.trace.status}
                    size="small"
                    color={traceStatusColor(detail.trace.status)}
                    sx={{ fontSize: 11 }}
                  />
                  {detail.intent?.primary_intent && (
                    <Chip
                      label={INTENT_LABEL[detail.intent.primary_intent] ?? detail.intent.primary_intent}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: 11 }}
                    />
                  )}
                  <Box sx={{ flex: 1 }} />
                  {detail.trace.total_latency_ms != null && (
                    <Typography variant="caption" color="text.secondary">
                      {detail.trace.total_latency_ms}ms
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.disabled">
                    {fmtTime(detail.trace.created_at)}
                  </Typography>
                </Stack>
                <Typography variant="body2" fontWeight={500}>
                  {queryLabel(detail.trace)}
                </Typography>
                {headerWarningSummary && (
                  <Typography variant="caption" color="warning.main" sx={{ mt: 0.75, display: "block" }}>
                    Warning: {headerWarningSummary}
                  </Typography>
                )}
              </Box>

              {/* Gate Bar */}
              {detail.gates.length > 0 && (
                <Box sx={{ px: 2, pt: 1.25 }}>
                  <GateBar gates={detail.gates} />
                </Box>
              )}

              {/* 탭 */}
              <Tabs
                value={activeTab}
                onChange={(_, v: number) => setActiveTab(v)}
                sx={{ px: 2, borderBottom: "1px solid", borderColor: "divider", minHeight: 38 }}
                TabIndicatorProps={{ style: { height: 2 } }}
              >
                {["의미분석", "Concept 탐지", "Agent 라우팅", "Tool 실행", "최종 답변 근거"].map((label, i) => (
                  <Tab key={i} label={label} sx={{ fontSize: 12, minHeight: 38, py: 0, px: 1.25 }} />
                ))}
              </Tabs>

              <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
                {activeTab === 0 && <IntentTab detail={detail} />}
                {activeTab === 1 && <ConceptTab detail={detail} />}
                {activeTab === 2 && <RoutingTab detail={detail} />}
                {activeTab === 3 && <ToolTab detail={detail} />}
                {activeTab === 4 && <AnswerTab detail={detail} />}
              </Box>
            </>
          ) : (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <Typography variant="caption" color="text.disabled">상세 정보를 불러올 수 없습니다</Typography>
            </Box>
          )}
        </Paper>
      </Stack>
    </AppShell>
  );
}
