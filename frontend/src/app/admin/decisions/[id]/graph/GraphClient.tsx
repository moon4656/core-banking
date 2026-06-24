"use client";

import "@xyflow/react/dist/style.css";

import dagre from "@dagrejs/dagre";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import HubRoundedIcon from "@mui/icons-material/HubRounded";
import RateReviewRoundedIcon from "@mui/icons-material/RateReviewRounded";
import RuleRoundedIcon from "@mui/icons-material/RuleRounded";
import {
  Background,
  Controls,
  Edge,
  MiniMap,
  Node,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import {
  DecisionAgentSelectionItem,
  DecisionConceptTrace,
  DecisionTraceResponse,
  DecisionToolExecution,
  fetchDecisionGraph,
  fetchDecisionTrace,
  GraphEdge,
  GraphNode,
} from "@/lib/api";
import { NODE_TYPES } from "./DecisionNodes";
import { ReviewDialog } from "./ReviewDialog";

const EDGE_COLOR: Record<string, string> = {
  HAS_INTENT: "#3b82f6",
  INFLUENCES: "#9ca3af",
  DETECTS: "#22c55e",
  HANDLED_BY: "#f59e0b",
  SELECTS: "#3b82f6",
  CALLS: "#22c55e",
  RETURNS: "#a78bfa",
  SCORED_BY: "#a78bfa",
  SUPPORTS: "#16a34a",
  PRODUCES: "#1d4ed8",
  SAVES_MEMORY: "#10b981",
};

const INTENT_LABEL: Record<string, string> = {
  INQUIRY: "조회",
  COMPARISON: "비교",
  RECOMMENDATION: "추천",
  APPLICATION: "신청",
  OTHER: "기타",
};

const INTENT_COLOR: Record<string, "info" | "secondary" | "warning" | "success" | "default"> = {
  INQUIRY: "info",
  COMPARISON: "secondary",
  RECOMMENDATION: "warning",
  APPLICATION: "success",
  OTHER: "default",
};

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value * 100)}%`;
}

function previewText(value: string, max = 120): string {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= max) return compact;
  return `${compact.slice(0, max)}...`;
}

// ── 노드 타입별 크기 (dagre 레이아웃 계산용) ──────────────
const NODE_SIZE: Record<string, { w: number; h: number }> = {
  USER_QUERY:      { w: 200, h: 56 },
  MEMORY_HINT:     { w: 180, h: 52 },
  INTENT:          { w: 180, h: 52 },
  CONCEPT:         { w: 220, h: 52 },
  LEADER_DECISION: { w: 200, h: 56 },
  SUB_AGENT:       { w: 190, h: 64 },
  TOOL_CALL:       { w: 190, h: 60 },
  RERANKING_SCORE: { w: 180, h: 52 },
  FINAL_RESPONSE:  { w: 200, h: 56 },
  MEMORY_WRITE:    { w: 200, h: 56 },
};
const DEFAULT_NODE_SIZE = { w: 180, h: 52 };

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: "TB",   // 위 → 아래
    ranksep: 90,     // 행 간격
    nodesep: 50,     // 같은 행 내 노드 간격
    edgesep: 20,
    marginx: 40,
    marginy: 40,
  });

  nodes.forEach((node) => {
    const nodeType = String((node.data as Record<string, unknown>).node_type ?? "");
    const { w, h } = NODE_SIZE[nodeType] ?? DEFAULT_NODE_SIZE;
    g.setNode(node.id, { width: w, height: h });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  return nodes.map((node) => {
    const { x, y, width, height } = g.node(node.id);
    return {
      ...node,
      position: { x: x - width / 2, y: y - height / 2 },
    };
  });
}

function toRFNodes(nodes: GraphNode[]): Node[] {
  return nodes.map((node) => ({
    id: node.id,
    type: node.node_type,
    position: node.position, // dagre가 덮어씀
    data: {
      label: node.label,
      node_type: node.node_type,
      status: node.status,
      duration_ms: node.duration_ms,
      data: node.data,
    },
  }));
}

function toRFEdges(edges: GraphEdge[]): Edge[] {
  return edges.map((edge) => {
    const color = EDGE_COLOR[edge.edge_type] ?? "#9ca3af";
    const isDashed =
      edge.edge_type === "INFLUENCES" || edge.data?.detection_type === "EXPANDED";

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label ?? undefined,
      type: "smoothstep",
      style: {
        stroke: color,
        strokeWidth: edge.weight > 0.8 ? 2 : 1.5,
        strokeDasharray: isDashed ? "5 3" : undefined,
      },
      markerEnd: { type: "arrowclosed" as const, color },
    };
  });
}

function DetailRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontWeight: 700 }}>
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          wordBreak: "break-word",
          fontFamily: mono ? "ui-monospace, SFMono-Regular, monospace" : "inherit",
        }}
      >
        {value || "-"}
      </Typography>
    </Box>
  );
}

function ExpandableTextCard({
  title,
  content,
}: {
  title: string;
  content: string;
}) {
  const compact = content.trim();
  if (!compact) {
    return (
      <Box sx={{ p: 1, border: "1px solid", borderColor: "divider", borderRadius: 2 }}>
        <Typography variant="caption" color="text.secondary">
          {title}
        </Typography>
        <Typography variant="body2">-</Typography>
      </Box>
    );
  }

  return (
    <Accordion disableGutters elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: "12px !important", overflow: "hidden" }}>
      <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ minHeight: 52 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
            {title}
          </Typography>
          <Typography variant="body2" sx={{ pr: 1 }}>
            {previewText(compact)}
          </Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {compact}
        </Typography>
      </AccordionDetails>
    </Accordion>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1 }}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}

function findAgentReason(
  trace: DecisionTraceResponse | undefined,
  agentName: string,
): DecisionAgentSelectionItem | undefined {
  if (!trace) return undefined;
  return [...trace.agent_selection.selected_agents, ...trace.agent_selection.rejected_agents].find(
    (item) => item.agent_name === agentName,
  );
}

function findConceptTrace(
  trace: DecisionTraceResponse | undefined,
  conceptId: string,
): DecisionConceptTrace | undefined {
  return trace?.concepts.find((item) => item.concept_id === conceptId);
}

function findToolTrace(
  trace: DecisionTraceResponse | undefined,
  nodeData: Record<string, unknown>,
): DecisionToolExecution | undefined {
  if (!trace) return undefined;
  const toolId = typeof nodeData.tool_id === "string" ? nodeData.tool_id : "";
  const agentId = typeof nodeData.agent_id === "string" ? nodeData.agent_id : "";
  return trace.tool_executions.find(
    (tool) => tool.tool_name === toolId && tool.agent_name === agentId,
  );
}

function OverviewPanel({ trace }: { trace?: DecisionTraceResponse }) {
  if (!trace) {
    return <Typography variant="body2" color="text.secondary">Trace 데이터를 불러오지 못했습니다.</Typography>;
  }

  return (
    <Box>
      <Section title="요청">
        <DetailRow label="질의" value={trace.user_query} />
        <DetailRow label="정규화 질의" value={trace.normalized_query ?? "-"} />
      </Section>

      <Section title="메모리">
        <DetailRow label="Short-term" value={`${trace.memory.short_memory.summary ?? "-"} (${trace.memory.short_memory.items_count}건)`} />
        <DetailRow label="Long-term" value={`${trace.memory.long_term_memory.summary ?? "-"} (${trace.memory.long_term_memory.items_count}건)`} />
        <DetailRow label="영향" value={[...trace.memory.short_memory.impact, ...trace.memory.long_term_memory.impact].join(" / ") || "-"} />
      </Section>

      <Section title="의도 분석">
        <DetailRow
          label="Intent"
          value={
            trace.intent_analysis.intent
              ? `${INTENT_LABEL[trace.intent_analysis.intent] ?? trace.intent_analysis.intent} (${formatPercent(trace.intent_analysis.confidence)})`
              : "-"
          }
        />
        <DetailRow label="키워드" value={trace.intent_analysis.keywords.join(", ") || "-"} />
        <DetailRow label="분석 이유" value={trace.intent_analysis.reason ?? "-"} />
      </Section>
    </Box>
  );
}

function NodeDetailPanel({ node, trace }: { node: Node | null; trace?: DecisionTraceResponse }) {
  if (!node) return <OverviewPanel trace={trace} />;

  const wrapped = node.data as Record<string, unknown>;
  const nodeType = String(wrapped.node_type ?? "");
  const status = String(wrapped.status ?? "");
  const durationMs = wrapped.duration_ms as number | null | undefined;
  const nodeData = (wrapped.data ?? {}) as Record<string, unknown>;

  if (nodeType === "MEMORY_HINT") {
    const isShort = nodeData.memory_type === "SHORT";
    const bucket = isShort ? trace?.memory.short_memory : trace?.memory.long_term_memory;

    return (
      <Box>
        <Section title={isShort ? "Short-term Memory" : "Long-term Memory"}>
          <DetailRow label="로드 여부" value={bucket?.loaded ? "예" : "아니오"} />
          <DetailRow label="요약" value={bucket?.summary ?? "-"} />
          <DetailRow label="건수" value={String(bucket?.items_count ?? nodeData.turns_loaded ?? 0)} />
          <DetailRow label="영향" value={bucket?.impact.join(", ") || "-"} />
          {(bucket?.items?.length ?? 0) > 0 ? (
            <Stack spacing={1}>
              {bucket?.items.map((item, index) => {
                const content = item.content ?? (item.question ? `Q. ${item.question}\nA. ${item.answer ?? "-"}` : item.answer ?? "-");
                return <ExpandableTextCard key={`${nodeType}-${index}`} title={`로드된 내역 ${index + 1}`} content={content} />;
              })}
            </Stack>
          ) : null}
        </Section>
      </Box>
    );
  }

  if (nodeType === "MEMORY_WRITE") {
    const preview = Array.isArray(nodeData.preview)
      ? nodeData.preview
          .map((item) =>
            typeof item === "object" && item !== null
              ? String((item as Record<string, unknown>).content ?? "-")
              : String(item),
          )
          .join("\n")
      : "";

    return (
      <Box>
        <Section title="Memory Save">
          <DetailRow label="메모리 타입" value={String(nodeData.memory_type ?? "-")} />
          <DetailRow label="저장 여부" value={nodeData.saved ? "성공" : "실패"} />
          <DetailRow label="저장 턴 수" value={String(nodeData.stored_turns ?? "-")} />
          <DetailRow label="LTM turn index" value={String(nodeData.turn_index ?? "-")} />
          <DetailRow label="사유" value={String(nodeData.reason ?? "-")} />
          {String(nodeData.question_summary ?? "").trim() ? (
            <ExpandableTextCard title="질문 요약" content={String(nodeData.question_summary)} />
          ) : null}
          {String(nodeData.answer_summary ?? "").trim() ? (
            <ExpandableTextCard title="답변 요약" content={String(nodeData.answer_summary)} />
          ) : null}
          {preview.trim() ? <ExpandableTextCard title="Short preview" content={preview} /> : null}
        </Section>
      </Box>
    );
  }

  if (nodeType === "INTENT") {
    return (
      <Box>
        <Section title="의도 분석">
          <DetailRow label="Intent" value={trace?.intent_analysis.intent ?? String(nodeData.intent_code ?? "-")} />
          <DetailRow label="Confidence" value={formatPercent(trace?.intent_analysis.confidence ?? (nodeData.confidence as number | undefined))} />
          <DetailRow label="키워드" value={trace?.intent_analysis.keywords.join(", ") || String((nodeData.keywords as string[] | undefined)?.join(", ") ?? "-")} />
          <DetailRow label="긴급도" value={trace?.intent_analysis.urgency ?? String(nodeData.urgency ?? "-")} />
          <DetailRow label="분석 이유" value={trace?.intent_analysis.reason ?? String(nodeData.reason ?? "-")} />
          <DetailRow label="처리 시간" value={durationMs ? `${durationMs} ms` : "-"} />
        </Section>
      </Box>
    );
  }

  if (nodeType === "CONCEPT") {
    const conceptId = String(nodeData.concept_id ?? wrapped.label ?? "-");
    const concept = findConceptTrace(trace, conceptId);
    return (
      <Box>
        <Section title="Concept">
          <DetailRow label="Concept ID" value={conceptId} mono />
          <DetailRow label="탐지 단계" value={concept?.detection_stage ?? String(nodeData.detection_type ?? "-")} />
          <DetailRow label="Confidence" value={formatPercent(concept?.confidence)} />
          <DetailRow label="Source" value={concept?.source_type ?? "-"} />
          <DetailRow label="Source Terms" value={concept?.source_terms.join(", ") || "-"} />
          <DetailRow label="탐지 근거" value={concept?.reason ?? "-"} />
        </Section>
      </Box>
    );
  }

  if (nodeType === "LEADER_DECISION") {
    return (
      <Box>
        <Section title="Leader Decision">
          <DetailRow label="설명" value={trace?.leader_decision.description ?? "-"} />
          <DetailRow label="근거" value={trace?.leader_decision.reason ?? "-"} />
          <DetailRow label="선택 Agent" value={trace?.agent_selection.selected_agents.map((item) => item.agent_name).join(", ") || "-"} />
          <DetailRow label="미선택 Agent" value={trace?.agent_selection.rejected_agents.map((item) => item.agent_name).join(", ") || "-"} />
          <DetailRow label="직접 탐지 Concept" value={trace?.leader_decision.direct_concepts.join(", ") || "-"} />
          <DetailRow label="확장 Concept" value={trace?.leader_decision.expanded_concepts.join(", ") || "-"} />
        </Section>
      </Box>
    );
  }

  if (nodeType === "SUB_AGENT") {
    const agentId = String(nodeData.agent_id ?? wrapped.label ?? "-");
    const agentReason = findAgentReason(trace, agentId);
    return (
      <Box>
        <Section title="Agent">
          <DetailRow label="Agent ID" value={agentId} mono />
          <DetailRow label="상태" value={status} />
          <DetailRow label="Score" value={String(agentReason?.score ?? "-")} />
          <DetailRow label="Matched Concepts" value={agentReason?.matched_concepts.join(", ") || "-"} />
          <DetailRow label="선택 사유" value={agentReason?.reason ?? String(nodeData.reason ?? "-")} />
          <DetailRow label="미선택 사유" value={agentReason?.rejection_reason ?? "-"} />
        </Section>
      </Box>
    );
  }

  if (nodeType === "TOOL_CALL") {
    const tool = findToolTrace(trace, nodeData);
    return (
      <Box>
        <Section title="Tool Execution">
          <DetailRow label="Tool" value={tool?.tool_name ?? String(nodeData.tool_id ?? wrapped.label ?? "-")} mono />
          <DetailRow label="Agent" value={tool?.agent_name ?? String(nodeData.agent_id ?? "-")} mono />
          <DetailRow label="상태" value={tool?.status ?? status} />
          <DetailRow label="처리 시간" value={tool?.latency_ms ? `${tool.latency_ms} ms` : "-"} />
          <DetailRow label="입력 요약" value={tool?.input_summary ?? "-"} />
          <DetailRow label="출력 요약" value={tool?.output_summary ?? "-"} />
        </Section>
      </Box>
    );
  }

  return (
    <Box>
      <Section title="노드 정보">
        <DetailRow label="노드 타입" value={nodeType} mono />
        <DetailRow label="상태" value={status} />
        <DetailRow label="처리 시간" value={durationMs ? `${durationMs} ms` : "-"} />
      </Section>
    </Box>
  );
}

function DecisionGraphView({ requestId }: { requestId: string }) {
  const router = useRouter();
  const [selected, setSelected] = useState<Node | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["decision-graph", requestId],
    queryFn: () => fetchDecisionGraph(requestId),
  });

  const { data: trace } = useQuery({
    queryKey: ["decision-trace-inline", requestId],
    queryFn: () => fetchDecisionTrace(requestId),
  });

  const rfEdges = useMemo(() => toRFEdges(data?.edges ?? []), [data]);
  const rfNodes = useMemo(() => {
    const nodes = toRFNodes(data?.nodes ?? []);
    return applyDagreLayout(nodes, rfEdges);
  }, [data, rfEdges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelected(node), []);
  const onPaneClick = useCallback(() => setSelected(null), []);

  if (isLoading) {
    return <Box sx={{ display: "flex", justifyContent: "center", pt: 10 }}><CircularProgress /></Box>;
  }

  if (error || !data) {
    return <Box sx={{ p: 4 }}><Typography color="error">그래프를 불러오지 못했습니다.</Typography></Box>;
  }

  const summary = data.summary;
  const userQuery = trace?.user_query ?? data.nodes.find((node) => node.node_type === "USER_QUERY")?.data?.message;
  const titleText = typeof userQuery === "string" && userQuery.trim().length > 0 ? userQuery : requestId;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box sx={{ px: 2, py: 1, borderBottom: "1px solid", borderColor: "divider", display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
        <Tooltip title="목록으로">
          <IconButton size="small" onClick={() => router.push("/admin/decisions")}>
            <ArrowBackRoundedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <HubRoundedIcon color="primary" sx={{ fontSize: 18 }} />
        <Tooltip title={`${titleText} (${requestId})`}>
          <Typography variant="subtitle2" fontWeight={700} noWrap sx={{ maxWidth: 560 }}>
            {titleText}
          </Typography>
        </Tooltip>
        <Chip label={requestId} size="small" variant="outlined" sx={{ maxWidth: 260 }} />
        <Box sx={{ flex: 1 }} />
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
          {summary.intent ? <Chip label={INTENT_LABEL[summary.intent] ?? summary.intent} size="small" color={INTENT_COLOR[summary.intent] ?? "default"} variant="outlined" /> : null}
          <Chip label={`Agent ${summary.selected_agents.length}`} size="small" variant="outlined" />
          <Chip label={`Concept ${summary.concept_count}`} size="small" variant="outlined" />
          <Chip label={`Tool ${summary.tool_count}`} size="small" variant="outlined" />
          <Chip label={`Node ${summary.node_count}`} size="small" variant="outlined" />
          <Chip label={`Edge ${summary.edge_count}`} size="small" variant="outlined" />
          <Chip
            label={`리뷰: ${data.review.status === "PENDING" ? "미평가" : data.review.status === "APPROVED" ? "승인" : "반려"}`}
            size="small"
            color={data.review.status === "APPROVED" ? "success" : data.review.status === "REJECTED" ? "error" : "default"}
          />
          <Button size="small" variant="outlined" startIcon={<RuleRoundedIcon sx={{ fontSize: 15 }} />} onClick={() => router.push(`/admin/decisions/${encodeURIComponent(requestId)}/trace`)}>
            Trace
          </Button>
          <Button size="small" variant={data.review.status === "PENDING" ? "contained" : "outlined"} startIcon={<RateReviewRoundedIcon sx={{ fontSize: 15 }} />} onClick={() => setReviewOpen(true)}>
            {data.review.status === "PENDING" ? "리뷰하기" : "리뷰 수정"}
          </Button>
        </Stack>
      </Box>

      <ReviewDialog open={reviewOpen} onClose={() => setReviewOpen(false)} requestId={requestId} existing={data.review} />

      <Box sx={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <Box sx={{ flex: 1, position: "relative" }}>
          <ReactFlow nodes={rfNodes} edges={rfEdges} nodeTypes={NODE_TYPES} onNodeClick={onNodeClick} onPaneClick={onPaneClick} fitView fitViewOptions={{ padding: 0.2 }} proOptions={{ hideAttribution: true }}>
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const nodeType = (node.data as Record<string, unknown>).node_type as string;
                const colors: Record<string, string> = {
                  USER_QUERY: "#93c5fd",
                  INTENT: "#3b82f6",
                  CONCEPT: "#22c55e",
                  LEADER_DECISION: "#f59e0b",
                  SUB_AGENT: "#60a5fa",
                  TOOL_CALL: "#4ade80",
                  MEMORY_WRITE: "#34d399",
                  FINAL_RESPONSE: "#16a34a",
                };
                return colors[nodeType] ?? "#d1d5db";
              }}
              style={{ backgroundColor: "#f9fafb" }}
            />
          </ReactFlow>
        </Box>

        <Box sx={{ width: 360, borderLeft: "1px solid", borderColor: "divider", flexShrink: 0, overflowY: "auto", bgcolor: "#fcfcfd" }}>
          <Box sx={{ px: 1.5, py: 1, borderBottom: "1px solid", borderColor: "divider" }}>
            <Typography variant="caption" fontWeight={800} color="text.secondary">
              {selected ? `${String((selected.data as Record<string, unknown>).node_type ?? "")} 상세` : "요청 상세"}
            </Typography>
          </Box>
          <Box sx={{ p: 1.5 }}>
            <NodeDetailPanel node={selected} trace={trace} />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export function DecisionGraphClient({ requestId }: { requestId: string }) {
  return (
    <AppShell title="질의 상세" noPadding>
      <ReactFlowProvider>
        <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <DecisionGraphView requestId={requestId} />
        </Box>
      </ReactFlowProvider>
    </AppShell>
  );
}
