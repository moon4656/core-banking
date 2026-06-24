"use client";

import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import RadioButtonCheckedRoundedIcon from "@mui/icons-material/RadioButtonCheckedRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SpeedRoundedIcon from "@mui/icons-material/SpeedRounded";
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import {
  fetchLatestRequestId,
  fetchMonitoringMetrics,
  getMonitoringStreamUrl,
  MonitoringMetrics,
  PipelineEvent,
} from "@/lib/api";

// ─────────────────────────────────────────────────────
// 상수
// ─────────────────────────────────────────────────────

const INTENT_LABEL: Record<string, string> = {
  INQUIRY: "조회",
  COMPARISON: "비교",
  RECOMMENDATION: "추천",
  APPLICATION: "신청",
  OTHER: "기타",
};

const INTENT_COLOR: Record<
  string,
  "info" | "secondary" | "warning" | "success" | "default"
> = {
  INQUIRY: "info",
  COMPARISON: "secondary",
  RECOMMENDATION: "warning",
  APPLICATION: "success",
  OTHER: "default",
};

// ─────────────────────────────────────────────────────
// StatCard
// ─────────────────────────────────────────────────────

function StatCard({
  title,
  value,
  unit,
  color,
}: {
  title: string;
  value: string | number;
  unit?: string;
  color?: string;
}) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 140 }}>
      <CardContent sx={{ pb: "12px !important" }}>
        <Typography variant="caption" color="text.secondary" noWrap>
          {title}
        </Typography>
        <Stack direction="row" alignItems="baseline" spacing={0.5} sx={{ mt: 0.5 }}>
          <Typography variant="h5" fontWeight={700} sx={{ color: color ?? "text.primary" }}>
            {value}
          </Typography>
          {unit ? (
            <Typography variant="caption" color="text.secondary">
              {unit}
            </Typography>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────
// PipelineEventRow
// ─────────────────────────────────────────────────────

function PipelineEventRow({ ev }: { ev: PipelineEvent }) {
  const isError = ev.status === "error";
  return (
    <Stack
      direction="row"
      alignItems="flex-start"
      spacing={1}
      sx={{
        py: 0.75,
        px: 1,
        borderRadius: 1,
        bgcolor: isError ? "error.50" : "transparent",
        "&:hover": { bgcolor: isError ? "error.100" : "action.hover" },
      }}
    >
      {isError ? (
        <ErrorRoundedIcon sx={{ fontSize: 15, color: "error.main", mt: 0.2, flexShrink: 0 }} />
      ) : (
        <CheckCircleRoundedIcon
          sx={{ fontSize: 15, color: "success.main", mt: 0.2, flexShrink: 0 }}
        />
      )}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap">
          <Typography variant="body2" fontWeight={500} noWrap>
            {ev.label}
          </Typography>
          {ev.agent_id ? (
            <Chip label={ev.agent_id} size="small" sx={{ fontSize: 10, height: 17 }} />
          ) : null}
          {ev.tool_id ? (
            <Chip
              label={ev.tool_id}
              size="small"
              color="secondary"
              variant="outlined"
              sx={{ fontSize: 10, height: 17 }}
            />
          ) : null}
          {ev.duration_ms != null ? (
            <Typography variant="caption" color="text.secondary">
              {ev.duration_ms}ms
            </Typography>
          ) : null}
        </Stack>
        {ev.ts ? (
          <Typography variant="caption" color="text.disabled">
            {new Date(ev.ts).toLocaleTimeString("ko-KR")}
          </Typography>
        ) : null}
      </Box>
    </Stack>
  );
}

// ─────────────────────────────────────────────────────
// MonitoringClient
// ─────────────────────────────────────────────────────

export function MonitoringClient() {
  const [hours, setHours] = useState(24);
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [streamStatus, setStreamStatus] = useState<
    "idle" | "connecting" | "streaming" | "done" | "error"
  >("idle");
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const latestIdRef = useRef<string | null>(null);
  const eventsEndRef = useRef<HTMLDivElement | null>(null);

  // ── 메트릭 로드 ──────────────────────────────────────────
  const loadMetrics = useCallback(async () => {
    setMetricsLoading(true);
    try {
      const data = await fetchMonitoringMetrics(hours);
      setMetrics(data);
    } finally {
      setMetricsLoading(false);
    }
  }, [hours]);

  useEffect(() => {
    void loadMetrics();
    const id = setInterval(() => void loadMetrics(), 30_000);
    return () => clearInterval(id);
  }, [loadMetrics]);

  // ── SSE 연결 ─────────────────────────────────────────────
  const connectSSE = useCallback((requestId: string) => {
    if (esRef.current) {
      esRef.current.close();
    }
    setEvents([]);
    setCurrentRequestId(requestId);
    setStreamStatus("connecting");

    const url = getMonitoringStreamUrl(requestId);
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setStreamStatus("streaming");

    es.onmessage = (msgEvent: MessageEvent) => {
      try {
        const payload = JSON.parse(msgEvent.data as string) as PipelineEvent & {
          event_type: string;
        };
        if (payload.event_type === "__DONE__" || payload.event_type === "__TIMEOUT__") {
          setStreamStatus("done");
          es.close();
          return;
        }
        setEvents((prev) => [...prev, payload as PipelineEvent]);
      } catch {
        // ignore malformed SSE frames
      }
    };

    es.onerror = () => {
      setStreamStatus("error");
      es.close();
    };
  }, []);

  // ── latest request_id 폴링 (3초) ─────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetchLatestRequestId();
        if (res.request_id && res.request_id !== latestIdRef.current) {
          latestIdRef.current = res.request_id;
          connectSSE(res.request_id);
        }
      } catch {
        // ignore polling errors
      }
    };

    void poll();
    const id = setInterval(() => void poll(), 3_000);
    return () => clearInterval(id);
  }, [connectSSE]);

  // ── 이벤트 목록 자동 스크롤 ──────────────────────────────
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  // ── 정리 ─────────────────────────────────────────────────
  useEffect(() => {
    return () => esRef.current?.close();
  }, []);

  const summary = metrics?.summary;

  return (
    <AppShell title="실시간 모니터링">
      {/* ── 헤더 ──────────────────────────────────── */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2.5 }}>
        <SpeedRoundedIcon color="primary" />
        <Typography variant="h6" fontWeight={700}>
          실시간 Agent 모니터링
        </Typography>
        <Box sx={{ flex: 1 }} />
        <Select
          size="small"
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          sx={{ fontSize: 13, height: 32 }}
        >
          {[1, 6, 24, 48, 168].map((h) => (
            <MenuItem key={h} value={h} sx={{ fontSize: 13 }}>
              최근 {h >= 24 ? `${h / 24}일` : `${h}시간`}
            </MenuItem>
          ))}
        </Select>
        <Tooltip title="메트릭 새로고침">
          <IconButton size="small" onClick={() => void loadMetrics()} disabled={metricsLoading}>
            {metricsLoading ? (
              <CircularProgress size={16} />
            ) : (
              <RefreshRoundedIcon fontSize="small" />
            )}
          </IconButton>
        </Tooltip>
      </Stack>

      {/* ── 요약 카드 ──────────────────────────────── */}
      <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2.5 }}>
        <StatCard title="총 요청" value={summary?.total_requests ?? "-"} />
        <StatCard
          title="성공률"
          value={
            summary != null ? `${(summary.success_rate * 100).toFixed(1)}%` : "-"
          }
          color={
            summary != null
              ? summary.success_rate >= 0.95
                ? "success.main"
                : summary.success_rate >= 0.8
                ? "warning.main"
                : "error.main"
              : undefined
          }
        />
        <StatCard
          title="평균 응답"
          value={summary?.avg_latency_ms != null ? Math.round(summary.avg_latency_ms) : "-"}
          unit="ms"
        />
        <StatCard
          title="오류 건수"
          value={summary?.error_count ?? "-"}
          color={summary?.error_count ? "error.main" : undefined}
        />
      </Stack>

      {/* ── 메인 2단 레이아웃 ──────────────────────── */}
      <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2 }}>
        {/* 실시간 파이프라인 이벤트 */}
        <Paper
          variant="outlined"
          sx={{ flex: 1.1, display: "flex", flexDirection: "column", minHeight: 360, maxHeight: 480 }}
        >
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <RadioButtonCheckedRoundedIcon
              sx={{
                fontSize: 14,
                color:
                  streamStatus === "streaming"
                    ? "success.main"
                    : streamStatus === "error"
                    ? "error.main"
                    : "text.disabled",
              }}
            />
            <Typography variant="subtitle2" fontWeight={600}>
              실시간 파이프라인 이벤트
            </Typography>
            {currentRequestId ? (
              <Chip
                label={currentRequestId.slice(0, 8) + "…"}
                size="small"
                sx={{ fontSize: 10, height: 18 }}
              />
            ) : null}
            <Box sx={{ flex: 1 }} />
            <Chip
              label={
                streamStatus === "streaming"
                  ? "연결 중"
                  : streamStatus === "connecting"
                  ? "접속 중"
                  : streamStatus === "done"
                  ? "완료"
                  : streamStatus === "error"
                  ? "오류"
                  : "대기"
              }
              size="small"
              color={
                streamStatus === "streaming"
                  ? "success"
                  : streamStatus === "error"
                  ? "error"
                  : "default"
              }
              variant="outlined"
              sx={{ fontSize: 10 }}
            />
          </Stack>

          <Box sx={{ flex: 1, overflowY: "auto", px: 0.5, py: 0.5 }}>
            {events.length === 0 ? (
              <Box
                sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}
              >
                <Typography variant="body2" color="text.disabled">
                  채팅 요청 대기 중…
                </Typography>
              </Box>
            ) : (
              <>
                {events.map((ev) => (
                  <PipelineEventRow key={ev.id} ev={ev} />
                ))}
                <div ref={eventsEndRef} />
              </>
            )}
          </Box>
        </Paper>

        {/* Agent / Tool 통계 */}
        <Stack spacing={2} sx={{ flex: 1 }}>
          {/* Agent 통계 */}
          <Paper variant="outlined" sx={{ flex: 1 }}>
            <Typography
              variant="subtitle2"
              fontWeight={600}
              sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
            >
              Agent 성능
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontSize: 12 }}>Agent</TableCell>
                  <TableCell align="right" sx={{ fontSize: 12 }}>호출</TableCell>
                  <TableCell align="right" sx={{ fontSize: 12 }}>성공률</TableCell>
                  <TableCell align="right" sx={{ fontSize: 12 }}>평균 ms</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {metrics?.agent_stats.length ? (
                  metrics.agent_stats.map((row) => (
                    <TableRow key={row.agent_id} hover>
                      <TableCell sx={{ fontSize: 12 }}>
                        <Typography variant="caption" fontWeight={500}>
                          {row.agent_id}
                        </Typography>
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 12 }}>
                        {row.call_count}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 12 }}>
                        <Typography
                          variant="caption"
                          sx={{
                            color:
                              row.success_rate >= 0.95
                                ? "success.main"
                                : row.success_rate >= 0.8
                                ? "warning.main"
                                : "error.main",
                            fontWeight: 600,
                          }}
                        >
                          {(row.success_rate * 100).toFixed(0)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 12 }}>
                        {Math.round(row.avg_latency_ms)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography variant="caption" color="text.disabled">
                        데이터 없음
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Paper>

          {/* Tool 통계 */}
          <Paper variant="outlined" sx={{ flex: 1 }}>
            <Typography
              variant="subtitle2"
              fontWeight={600}
              sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
            >
              Tool 성능
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontSize: 12 }}>Tool</TableCell>
                  <TableCell align="right" sx={{ fontSize: 12 }}>호출</TableCell>
                  <TableCell align="right" sx={{ fontSize: 12 }}>성공률</TableCell>
                  <TableCell align="right" sx={{ fontSize: 12 }}>평균 ms</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {metrics?.tool_stats.length ? (
                  metrics.tool_stats.map((row) => (
                    <TableRow key={row.tool_id} hover>
                      <TableCell sx={{ fontSize: 12 }}>
                        <Typography variant="caption" fontWeight={500}>
                          {row.tool_id}
                        </Typography>
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 12 }}>
                        {row.call_count}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 12 }}>
                        <Typography
                          variant="caption"
                          sx={{
                            color:
                              row.success_rate >= 0.95
                                ? "success.main"
                                : row.success_rate >= 0.8
                                ? "warning.main"
                                : "error.main",
                            fontWeight: 600,
                          }}
                        >
                          {(row.success_rate * 100).toFixed(0)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 12 }}>
                        {Math.round(row.avg_latency_ms)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography variant="caption" color="text.disabled">
                        데이터 없음
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Paper>
        </Stack>
      </Stack>

      {/* ── 하단 3단 레이아웃 ──────────────────────── */}
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        {/* 의도 분포 */}
        <Paper variant="outlined" sx={{ flex: 1 }}>
          <Typography
            variant="subtitle2"
            fontWeight={600}
            sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
          >
            의도 분포
          </Typography>
          <Box sx={{ px: 2, py: 1.5 }}>
            {metrics?.intent_distribution &&
            Object.keys(metrics.intent_distribution).length ? (
              Object.entries(metrics.intent_distribution)
                .sort(([, a], [, b]) => b - a)
                .map(([intent, count]) => {
                  const total = Object.values(metrics.intent_distribution).reduce(
                    (s, v) => s + v,
                    0,
                  );
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <Box key={intent} sx={{ mb: 1 }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.35 }}>
                        <Chip
                          label={INTENT_LABEL[intent] ?? intent}
                          color={INTENT_COLOR[intent] ?? "default"}
                          size="small"
                          sx={{ fontSize: 10, height: 18, minWidth: 42 }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {count}건 ({pct.toFixed(0)}%)
                        </Typography>
                      </Stack>
                      <Box
                        sx={{
                          height: 6,
                          borderRadius: 3,
                          bgcolor: "action.selected",
                          overflow: "hidden",
                        }}
                      >
                        <Box
                          sx={{
                            height: "100%",
                            width: `${pct}%`,
                            bgcolor: "primary.main",
                            borderRadius: 3,
                            transition: "width 0.4s ease",
                          }}
                        />
                      </Box>
                    </Box>
                  );
                })
            ) : (
              <Typography variant="caption" color="text.disabled">
                데이터 없음
              </Typography>
            )}
          </Box>
        </Paper>

        {/* 파이프라인 단계별 지연 */}
        <Paper variant="outlined" sx={{ flex: 1 }}>
          <Typography
            variant="subtitle2"
            fontWeight={600}
            sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
          >
            단계별 평균 지연
          </Typography>
          <Box sx={{ px: 2, py: 1.5 }}>
            {metrics?.pipeline_latency.length ? (
              (() => {
                const maxMs = Math.max(...metrics.pipeline_latency.map((r) => r.avg_ms), 1);
                return metrics.pipeline_latency.map((row) => (
                  <Box key={row.event_type} sx={{ mb: 1 }}>
                    <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.35 }}>
                      <Typography variant="caption" sx={{ minWidth: 120 }} noWrap>
                        {row.label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {Math.round(row.avg_ms)}ms
                      </Typography>
                    </Stack>
                    <Box
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: "action.selected",
                        overflow: "hidden",
                      }}
                    >
                      <Box
                        sx={{
                          height: "100%",
                          width: `${(row.avg_ms / maxMs) * 100}%`,
                          bgcolor: "info.main",
                          borderRadius: 3,
                          transition: "width 0.4s ease",
                        }}
                      />
                    </Box>
                  </Box>
                ));
              })()
            ) : (
              <Typography variant="caption" color="text.disabled">
                데이터 없음
              </Typography>
            )}
          </Box>
        </Paper>

        {/* 최근 오류 */}
        <Paper variant="outlined" sx={{ flex: 1 }}>
          <Typography
            variant="subtitle2"
            fontWeight={600}
            sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
          >
            최근 오류 (최대 5건)
          </Typography>
          <Box sx={{ px: 1, py: 0.75 }}>
            {metrics?.recent_errors.length ? (
              metrics.recent_errors.map((err, idx) => (
                <Box key={idx}>
                  {idx > 0 ? <Divider sx={{ my: 0.5 }} /> : null}
                  <Stack direction="row" alignItems="flex-start" spacing={0.75} sx={{ py: 0.5, px: 1 }}>
                    <ErrorRoundedIcon
                      sx={{ fontSize: 14, color: "error.main", mt: 0.2, flexShrink: 0 }}
                    />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="caption" fontWeight={500} display="block">
                        {err.event_type}
                      </Typography>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap">
                        {err.agent_id ? (
                          <Chip
                            label={err.agent_id}
                            size="small"
                            sx={{ fontSize: 9, height: 16 }}
                          />
                        ) : null}
                        {err.tool_id ? (
                          <Chip
                            label={err.tool_id}
                            size="small"
                            color="secondary"
                            variant="outlined"
                            sx={{ fontSize: 9, height: 16 }}
                          />
                        ) : null}
                      </Stack>
                      {err.ts ? (
                        <Typography variant="caption" color="text.disabled" display="block">
                          {new Date(err.ts).toLocaleString("ko-KR")}
                        </Typography>
                      ) : null}
                    </Box>
                  </Stack>
                </Box>
              ))
            ) : (
              <Box sx={{ px: 1, py: 1.5 }}>
                <Typography variant="caption" color="text.disabled">
                  오류 없음
                </Typography>
              </Box>
            )}
          </Box>
        </Paper>
      </Stack>
    </AppShell>
  );
}

