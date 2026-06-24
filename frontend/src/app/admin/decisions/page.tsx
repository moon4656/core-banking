"use client";

import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import RuleRoundedIcon from "@mui/icons-material/RuleRounded";
import {
  Box,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { DataGrid, GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { DecisionListItem, fetchDecisions } from "@/lib/api";

const INTENT_COLOR: Record<string, "info" | "secondary" | "warning" | "success" | "default"> = {
  INQUIRY: "info",
  COMPARISON: "secondary",
  RECOMMENDATION: "warning",
  APPLICATION: "success",
  OTHER: "default",
};

const INTENT_LABEL: Record<string, string> = {
  INQUIRY: "조회",
  COMPARISON: "비교",
  RECOMMENDATION: "추천",
  APPLICATION: "신청",
  OTHER: "기타",
};

const REVIEW_COLOR: Record<string, "default" | "success" | "error" | "warning"> = {
  PENDING: "default",
  APPROVED: "success",
  REJECTED: "error",
};

const REVIEW_LABEL: Record<string, string> = {
  PENDING: "미평가",
  APPROVED: "확인",
  REJECTED: "반려",
};

const AGENT_SHORT: Record<string, string> = {
  PRODUCT_AGENT: "상품",
  RATE_AGENT: "금리",
  POLICY_AGENT: "정책",
  SEARCH_AGENT: "검색",
};

function buildColumns(
  onOpenGraph: (id: string) => void,
  onOpenTrace: (id: string) => void,
): GridColDef<DecisionListItem>[] {
  return [
    {
      field: "query_preview",
      headerName: "질문",
      flex: 2,
      minWidth: 220,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", height: "100%", gap: 0.5 }}>
          <AccountTreeRoundedIcon sx={{ fontSize: 14, color: "text.secondary", flexShrink: 0 }} />
          <Typography variant="body2" noWrap sx={{ color: "text.primary" }}>
            {params.value ?? "-"}
          </Typography>
        </Box>
      ),
    },
    {
      field: "intent",
      headerName: "의도",
      width: 100,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
          {params.value ? (
            <Chip
              label={INTENT_LABEL[params.value as string] ?? params.value}
              color={INTENT_COLOR[params.value as string] ?? "default"}
              size="small"
              variant="outlined"
              sx={{ fontSize: 11 }}
            />
          ) : (
            <Typography variant="caption" color="text.disabled">
              -
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: "selected_agents",
      headerName: "선택 Agent",
      width: 180,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => {
        const agents = (params.value as string[]) ?? [];
        return (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%", gap: 0.4, flexWrap: "wrap" }}>
            {agents.length ? (
              agents.map((agent) => (
                <Chip
                  key={agent}
                  label={AGENT_SHORT[agent] ?? agent}
                  size="small"
                  sx={{ fontSize: 10, height: 18 }}
                />
              ))
            ) : (
              <Typography variant="caption" color="text.disabled">
                없음
              </Typography>
            )}
          </Box>
        );
      },
    },
    {
      field: "node_count",
      headerName: "Node",
      width: 76,
      align: "center",
      headerAlign: "center",
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <Typography variant="body2">{params.value as number}</Typography>
        </Box>
      ),
    },
    {
      field: "tool_count",
      headerName: "Tool",
      width: 76,
      align: "center",
      headerAlign: "center",
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <Typography variant="body2">{params.value as number}</Typography>
        </Box>
      ),
    },
    {
      field: "review_status",
      headerName: "리뷰",
      width: 92,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
          <Chip
            label={REVIEW_LABEL[params.value as string] ?? params.value}
            color={REVIEW_COLOR[params.value as string] ?? "default"}
            size="small"
            sx={{ fontSize: 11 }}
          />
        </Box>
      ),
    },
    {
      field: "created_at",
      headerName: "생성 시각",
      width: 170,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
          <Typography variant="caption" color="text.secondary">
            {params.value ? new Date(params.value as string).toLocaleString("ko-KR") : "-"}
          </Typography>
        </Box>
      ),
    },
    {
      field: "graph_action",
      headerName: "Graph",
      width: 78,
      sortable: false,
      filterable: false,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <Tooltip title="Decision Graph 보기">
            <IconButton
              size="small"
              onClick={(event) => {
                event.stopPropagation();
                onOpenGraph(params.row.request_id);
              }}
            >
              <OpenInNewRoundedIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
    {
      field: "trace_action",
      headerName: "Trace",
      width: 78,
      sortable: false,
      filterable: false,
      renderCell: (params: GridRenderCellParams<DecisionListItem>) => (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <Tooltip title="Decision Trace 보기">
            <IconButton
              size="small"
              onClick={(event) => {
                event.stopPropagation();
                onOpenTrace(params.row.request_id);
              }}
            >
              <RuleRoundedIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
  ];
}

export default function DecisionsPage() {
  const router = useRouter();
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 20 });

  const { data, isLoading } = useQuery({
    queryKey: ["decisions", paginationModel.page, paginationModel.pageSize],
    queryFn: () => fetchDecisions(paginationModel.page + 1, paginationModel.pageSize),
  });

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleOpenGraph = (requestId: string) => {
    router.push(`/admin/decisions/${encodeURIComponent(requestId)}/graph`);
  };

  const handleOpenTrace = (requestId: string) => {
    router.push(`/admin/decisions/${encodeURIComponent(requestId)}/trace`);
  };

  const columns = buildColumns(handleOpenGraph, handleOpenTrace);

  return (
    <AppShell title="Decision Graph">
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <AccountTreeRoundedIcon color="primary" />
        <Typography variant="h6" fontWeight={700}>
          Decision Graph 목록
        </Typography>
        {!isLoading ? (
          <Typography variant="body2" color="text.secondary">
            총 {total}건
          </Typography>
        ) : null}
      </Stack>

      {isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", pt: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(row) => row.request_id}
          rowCount={total}
          paginationMode="server"
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 20, 50]}
          onRowClick={(params) => handleOpenGraph(params.row.request_id)}
          disableColumnFilter
          disableColumnMenu
          sx={{
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 2,
            "& .MuiDataGrid-row": { cursor: "pointer" },
          }}
        />
      )}
    </AppShell>
  );
}
