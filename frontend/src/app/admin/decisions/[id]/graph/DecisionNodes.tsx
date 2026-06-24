"use client";

import { Handle, Position } from "@xyflow/react";
import { Box, Chip, Typography } from "@mui/material";

const NODE_STYLE: Record<string, { bg: string; border: string; textColor: string }> = {
  USER_QUERY: { bg: "#f0f9ff", border: "#93c5fd", textColor: "#1e40af" },
  MEMORY_HINT: { bg: "#f5f3ff", border: "#c4b5fd", textColor: "#6d28d9" },
  MEMORY_WRITE: { bg: "#eefdf5", border: "#34d399", textColor: "#166534" },
  INTENT: { bg: "#dbeafe", border: "#3b82f6", textColor: "#1d4ed8" },
  CONCEPT: { bg: "#dcfce7", border: "#22c55e", textColor: "#166534" },
  LEADER_DECISION: { bg: "#fef3c7", border: "#f59e0b", textColor: "#92400e" },
  SUB_AGENT: { bg: "#dbeafe", border: "#60a5fa", textColor: "#1e3a8a" },
  TOOL_CALL: { bg: "#f0fdf4", border: "#22c55e", textColor: "#14532d" },
  RERANKING_SCORE: { bg: "#faf5ff", border: "#a78bfa", textColor: "#4c1d95" },
  FINAL_RESPONSE: { bg: "#f0fdf4", border: "#16a34a", textColor: "#14532d" },
  default: { bg: "#f9fafb", border: "#d1d5db", textColor: "#374151" },
};

const STATUS_STYLE: Record<string, Partial<{ bg: string; border: string }>> = {
  FAILED: { bg: "#fef2f2", border: "#fca5a5" },
  SKIPPED: { bg: "#f9fafb", border: "#e5e7eb" },
};

type NodeData = {
  label: string;
  node_type: string;
  status: string;
  duration_ms?: number | null;
  data: Record<string, unknown>;
};

function nodeStyle(nodeType: string, status: string) {
  const base = NODE_STYLE[nodeType] ?? NODE_STYLE.default;
  const override = STATUS_STYLE[status] ?? {};
  return { ...base, ...override };
}

function DurationChip({ ms }: { ms: number | null | undefined }) {
  if (!ms) return null;
  return (
    <Chip
      label={`${ms}ms`}
      size="small"
      sx={{ fontSize: 9, height: 16, ml: 0.5, "& .MuiChip-label": { px: 0.75 } }}
    />
  );
}

function BaseNode({
  data,
  children,
  minWidth = 140,
}: {
  data: NodeData;
  children?: React.ReactNode;
  minWidth?: number;
}) {
  const style = nodeStyle(data.node_type, data.status);
  const isSkipped = data.status === "SKIPPED";
  const isFailed = data.status === "FAILED";

  return (
    <Box
      sx={{
        minWidth,
        maxWidth: 220,
        px: 1.25,
        py: 0.75,
        borderRadius: "10px",
        border: `1.5px solid ${style.border}`,
        backgroundColor: style.bg,
        opacity: isSkipped ? 0.45 : 1,
        boxShadow: isFailed ? "0 0 0 2px #fca5a5" : "0 1px 3px rgba(0,0,0,0.08)",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0.4 }} />
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <Typography variant="caption" sx={{ fontWeight: 700, color: style.textColor, lineHeight: 1.2 }}>
          {data.label}
        </Typography>
        <DurationChip ms={data.duration_ms} />
      </Box>
      {children}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0.4 }} />
    </Box>
  );
}

export function UserQueryNode({ data }: { data: NodeData }) {
  const message = (data.data.message as string) ?? "";
  return (
    <BaseNode data={data} minWidth={180}>
      <Typography variant="caption" color="text.secondary" noWrap sx={{ display: "block", maxWidth: 200 }}>
        {message.slice(0, 30)}
        {message.length > 30 ? "..." : ""}
      </Typography>
    </BaseNode>
  );
}

export function MemoryHintNode({ data }: { data: NodeData }) {
  const turns = (data.data.turns_loaded as number) ?? 0;
  const memoryType = (data.data.memory_type as string) ?? "";
  return (
    <BaseNode data={data} minWidth={120}>
      <Typography variant="caption" color="text.secondary">
        {memoryType === "SHORT" ? "Short" : "LTM"} {turns}건
      </Typography>
    </BaseNode>
  );
}

export function MemoryWriteNode({ data }: { data: NodeData }) {
  const memoryType = (data.data.memory_type as string) ?? "";
  const saved = Boolean(data.data.saved);
  const turns = data.data.stored_turns as number | undefined;
  const turnIndex = data.data.turn_index as number | undefined;
  return (
    <BaseNode data={data} minWidth={150}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.25, flexWrap: "wrap" }}>
        <Chip
          label={saved ? "저장" : "실패"}
          size="small"
          color={saved ? "success" : "error"}
          sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }}
        />
        {memoryType === "SHORT" && turns !== undefined ? (
          <Typography variant="caption" color="text.secondary">
            총 {turns}턴
          </Typography>
        ) : null}
        {memoryType === "LTM" && turnIndex !== undefined ? (
          <Typography variant="caption" color="text.secondary">
            turn {turnIndex}
          </Typography>
        ) : null}
      </Box>
    </BaseNode>
  );
}

export function IntentNode({ data }: { data: NodeData }) {
  const intent = (data.data.intent_code as string) ?? "";
  const confidence = data.data.confidence as number;
  const keywords = (data.data.keywords as string[]) ?? [];
  return (
    <BaseNode data={data}>
      <Box sx={{ display: "flex", gap: 0.4, flexWrap: "wrap", mt: 0.25 }}>
        <Chip label={intent} size="small" color="info" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
        {confidence != null ? (
          <Chip label={`${Math.round(confidence * 100)}%`} size="small" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
        ) : null}
      </Box>
      {keywords.length > 0 ? (
        <Typography variant="caption" color="text.secondary" noWrap sx={{ display: "block", mt: 0.25 }}>
          {keywords.slice(0, 3).join(", ")}
        </Typography>
      ) : null}
    </BaseNode>
  );
}

export function ConceptNode({ data }: { data: NodeData }) {
  const detectionType = (data.data.detection_type as string) ?? "DIRECT";
  const label = (data.label ?? "").replace("CONCEPT_", "");
  return (
    <BaseNode data={{ ...data, label }} minWidth={110}>
      <Chip
        label={detectionType === "DIRECT" ? "직접" : "확장"}
        size="small"
        sx={{
          fontSize: 9,
          height: 14,
          mt: 0.25,
          bgcolor: detectionType === "DIRECT" ? "#bbf7d0" : "#d1fae5",
          "& .MuiChip-label": { px: 0.5 },
        }}
      />
    </BaseNode>
  );
}

export function LeaderDecisionNodeView({ data }: { data: NodeData }) {
  const confidence = data.data.confidence_score as number;
  const agents = (data.data.selected_agent_ids as string[]) ?? [];
  return (
    <BaseNode data={data} minWidth={160}>
      <Box sx={{ display: "flex", gap: 0.4, flexWrap: "wrap", mt: 0.25 }}>
        {confidence != null ? (
          <Chip label={`${Math.round(confidence * 100)}%`} size="small" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
        ) : null}
        <Chip label={`Agent ${agents.length}`} size="small" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
      </Box>
    </BaseNode>
  );
}

export function SubAgentNode({ data }: { data: NodeData }) {
  const status = data.data.status as string;
  const isSkipped = status === "SKIPPED";
  const concepts = (data.data.concept_ids as string[]) ?? [];
  return (
    <BaseNode data={data} minWidth={130}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.25 }}>
        <Chip
          label={isSkipped ? "미선택" : "선택"}
          size="small"
          color={isSkipped ? "default" : "primary"}
          sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }}
        />
        {concepts.length > 0 ? (
          <Typography variant="caption" color="text.secondary">
            {concepts.length}개
          </Typography>
        ) : null}
      </Box>
    </BaseNode>
  );
}

export function ToolCallNode({ data }: { data: NodeData }) {
  const status = data.data.status as string;
  const isFailed = status === "FAILED";
  const label = (data.label ?? "").replace("MOCK_", "");
  return (
    <BaseNode data={{ ...data, label }} minWidth={130}>
      <Chip
        label={isFailed ? "실패" : "성공"}
        size="small"
        color={isFailed ? "error" : "success"}
        sx={{ fontSize: 10, height: 16, mt: 0.25, "& .MuiChip-label": { px: 0.5 } }}
      />
    </BaseNode>
  );
}

export function RerankingNode({ data }: { data: NodeData }) {
  const top = (data.data.top as string) ?? "";
  return (
    <BaseNode data={data} minWidth={140}>
      {top ? (
        <Typography variant="caption" color="text.secondary" noWrap>
          1위 {top.replace("MOCK_", "")}
        </Typography>
      ) : null}
    </BaseNode>
  );
}

export function FinalResponseNode({ data }: { data: NodeData }) {
  const answerLength = data.data.answer_length as number;
  const model = (data.data.llm_model as string) ?? "";
  const fallback = Boolean(data.data.template_fallback);
  return (
    <BaseNode data={data} minWidth={150}>
      <Box sx={{ display: "flex", gap: 0.4, mt: 0.25, flexWrap: "wrap" }}>
        <Chip label={model} size="small" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
        {answerLength ? (
          <Chip label={`${answerLength}자`} size="small" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
        ) : null}
        {fallback ? (
          <Chip label="템플릿" size="small" color="warning" sx={{ fontSize: 10, height: 16, "& .MuiChip-label": { px: 0.5 } }} />
        ) : null}
      </Box>
    </BaseNode>
  );
}

export const NODE_TYPES = {
  USER_QUERY: UserQueryNode,
  MEMORY_HINT: MemoryHintNode,
  MEMORY_WRITE: MemoryWriteNode,
  INTENT: IntentNode,
  CONCEPT: ConceptNode,
  LEADER_DECISION: LeaderDecisionNodeView,
  SUB_AGENT: SubAgentNode,
  TOOL_CALL: ToolCallNode,
  RERANKING_SCORE: RerankingNode,
  FINAL_RESPONSE: FinalResponseNode,
};
