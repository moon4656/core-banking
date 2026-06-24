"use client";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import SchemaRoundedIcon from "@mui/icons-material/SchemaRounded";
import TimelineRoundedIcon from "@mui/icons-material/TimelineRounded";
import TravelExploreRoundedIcon from "@mui/icons-material/TravelExploreRounded";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/AppShell";
import {
  DecisionAgentSelectionItem,
  DecisionConceptTrace,
  DecisionToolExecution,
  fetchDecisionTrace,
} from "@/lib/api";

const INTENT_LABEL: Record<string, string> = {
  INQUIRY: "조회",
  COMPARISON: "비교",
  RECOMMENDATION: "추천",
  APPLICATION: "신청",
  OTHER: "기타",
};

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value * 100)}%`;
}

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${value} ms`;
}

function previewText(value: string, max = 120): string {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= max) return compact;
  return `${compact.slice(0, max)}...`;
}

function ExpandableTextCard({ title, content }: { title: string; content: string }) {
  const compact = content.trim();
  return (
    <Accordion disableGutters elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: "12px !important", overflow: "hidden" }}>
      <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ minHeight: 52 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
            {title}
          </Typography>
          <Typography variant="body2">{previewText(compact || "-")}</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {compact || "-"}
        </Typography>
      </AccordionDetails>
    </Accordion>
  );
}

function SectionCard({
  title,
  icon,
  subtitle,
  children,
}: {
  title: string;
  icon: ReactNode;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <Paper elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3, p: 2, background: "linear-gradient(180deg, rgba(248,250,252,0.98) 0%, rgba(255,255,255,1) 100%)" }}>
      <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 1 }}>
        <Box sx={{ width: 34, height: 34, borderRadius: 2, display: "grid", placeItems: "center", backgroundColor: "#e0f2fe", color: "#0369a1" }}>
          {icon}
        </Box>
        <Box>
          <Typography variant="h6" fontWeight={700}>{title}</Typography>
          {subtitle ? <Typography variant="body2" color="text.secondary">{subtitle}</Typography> : null}
        </Box>
      </Stack>
      {children}
    </Paper>
  );
}

function AgentReasonCard({ title, items, selected }: { title: string; items: DecisionAgentSelectionItem[]; selected: boolean }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2.5, backgroundColor: selected ? "#f0fdf4" : "#fff7ed", borderColor: selected ? "#86efac" : "#fdba74" }}>
      <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>{title}</Typography>
      <Stack spacing={1}>
        {items.length ? items.map((item) => (
          <Box key={`${title}-${item.agent_name}`} sx={{ p: 1, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.72)" }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }} flexWrap="wrap" useFlexGap>
              <Chip label={item.agent_name} size="small" color={selected ? "success" : "warning"} />
              <Chip label={`score ${item.score ?? 0}`} size="small" variant="outlined" />
            </Stack>
            <Typography variant="body2">{item.reason}</Typography>
            {!selected && item.rejection_reason ? <Typography variant="caption" color="text.secondary">제외 사유: {item.rejection_reason}</Typography> : null}
          </Box>
        )) : <Typography variant="body2" color="text.secondary">항목이 없습니다.</Typography>}
      </Stack>
    </Paper>
  );
}

function ConceptCard({ concept }: { concept: DecisionConceptTrace }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.25, borderRadius: 2.5 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.75 }} flexWrap="wrap" useFlexGap>
        <Chip label={concept.concept_id} size="small" color="info" />
        <Chip label={concept.detection_stage} size="small" variant="outlined" />
        <Chip label={`confidence ${formatPercent(concept.confidence)}`} size="small" variant="outlined" />
      </Stack>
      {concept.reason ? <Typography variant="body2">{concept.reason}</Typography> : null}
    </Paper>
  );
}

function ToolCard({ tool }: { tool: DecisionToolExecution }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2.5 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
        <Chip label={tool.tool_name} size="small" color={tool.status === "success" ? "success" : "error"} />
        <Chip label={tool.agent_name} size="small" variant="outlined" />
        <Chip label={formatMs(tool.latency_ms)} size="small" variant="outlined" />
      </Stack>
      <Typography variant="body2" sx={{ mb: 0.5 }}>입력 요약: {tool.input_summary ?? "-"}</Typography>
      <Typography variant="body2" sx={{ mb: 0.5 }}>출력 요약: {tool.output_summary ?? "-"}</Typography>
    </Paper>
  );
}

export function DecisionTraceClient({ requestId }: { requestId: string }) {
  const router = useRouter();
  const { data, isLoading, error } = useQuery({
    queryKey: ["decision-trace", requestId],
    queryFn: () => fetchDecisionTrace(requestId),
  });

  if (isLoading) {
    return <AppShell title="Decision Trace"><Box sx={{ display: "flex", justifyContent: "center", pt: 10 }}><CircularProgress /></Box></AppShell>;
  }

  if (error || !data) {
    return <AppShell title="Decision Trace"><Alert severity="error">Decision trace를 불러오지 못했습니다.</Alert></AppShell>;
  }

  return (
    <AppShell title="Decision Trace">
      <Stack spacing={2.5}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Tooltip title="Decision Graph로 돌아가기">
            <IconButton onClick={() => router.push(`/admin/decisions/${encodeURIComponent(requestId)}/graph`)}>
              <ArrowBackRoundedIcon />
            </IconButton>
          </Tooltip>
          <Typography variant="h5" fontWeight={800}>Request Trace</Typography>
          <Chip label={data.request_id} size="small" variant="outlined" />
        </Stack>

        <SectionCard title="Summary View" icon={<TimelineRoundedIcon fontSize="small" />} subtitle="질문, intent, 선택 agent, 메모리, 전체 latency를 먼저 확인합니다.">
          <Stack spacing={1.5}>
            <Box>
              <Typography variant="caption" color="text.secondary">사용자 질문</Typography>
              <Typography variant="body1" fontWeight={600}>{data.user_query}</Typography>
            </Box>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
              <Chip label={`Intent ${INTENT_LABEL[data.intent_analysis.intent ?? ""] ?? data.intent_analysis.intent ?? "-"}`} color="info" />
              <Chip label={`Confidence ${formatPercent(data.intent_analysis.confidence)}`} variant="outlined" />
              <Chip label={`Total ${formatMs(data.latency.total_ms)}`} color="success" variant="outlined" />
            </Stack>
            <Divider />
            <Typography variant="body2">Short: {data.memory.short_memory.summary ?? "-"}</Typography>
            <Typography variant="body2">Long-term: {data.memory.long_term_memory.summary ?? "-"}</Typography>
          </Stack>
        </SectionCard>

        <SectionCard title="Decision Trace View" icon={<SchemaRoundedIcon fontSize="small" />} subtitle="개념 탐지, agent 선택/제외 사유, memory detail, 단계별 latency를 추적합니다.">
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>Leader Decision</Typography>
              <Typography variant="body2">{data.leader_decision.reason ?? data.leader_decision.description ?? "-"}</Typography>
            </Box>

            <Box sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" } }}>
              {data.concepts.map((concept) => <ConceptCard key={`${concept.concept_id}-${concept.detection_stage}`} concept={concept} />)}
            </Box>

            <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", xl: "repeat(2, minmax(0, 1fr))" } }}>
              <AgentReasonCard title="선택 Agent" items={data.agent_selection.selected_agents} selected />
              <AgentReasonCard title="미선택 Agent" items={data.agent_selection.rejected_agents} selected={false} />
            </Box>

            <Box>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>Memory Details</Typography>
              <Stack spacing={1}>
                {data.memory.short_memory.items.map((item, index) => (
                  <ExpandableTextCard key={`short-${index}`} title={`Short memory ${index + 1}`} content={item.content ?? item.question ?? item.answer ?? "-"} />
                ))}
                {data.memory.long_term_memory.items.map((item, index) => (
                  <ExpandableTextCard key={`ltm-${index}`} title={`Long-term memory ${index + 1}`} content={`Q. ${item.question ?? "-"}\nA. ${item.answer ?? "-"}`} />
                ))}
              </Stack>
            </Box>

            <Box>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>단계별 처리 시간</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {(data.latency.steps ?? []).map((step) => <Chip key={step.step} label={`${step.step} ${step.latency_ms}ms`} variant="outlined" />)}
              </Stack>
            </Box>
          </Stack>
        </SectionCard>

        <SectionCard title="Evidence / Tool View" icon={<TravelExploreRoundedIcon fontSize="small" />} subtitle="Tool 실행, reranking 기준, final answer grounding을 확인합니다.">
          <Stack spacing={2}>
            <Stack spacing={1}>
              {data.tool_executions.map((tool, index) => <ToolCard key={`${tool.tool_name}-${index}`} tool={tool} />)}
            </Stack>
            <Typography variant="body2">{data.reranking.reason ?? "-"}</Typography>
            <ExpandableTextCard title="Final Answer Grounding" content={data.final_answer.answer_summary ?? data.final_answer.answer} />
          </Stack>
        </SectionCard>
      </Stack>
    </AppShell>
  );
}
