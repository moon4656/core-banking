"use client";

import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import {
  Alert,
  Box,
  Button,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GridColDef, GridRowParams } from "@mui/x-data-grid";
import { useMemo, useState } from "react";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { apiDelete, apiGet, apiPost, apiPut, ApiError } from "@/lib/api";
import { AgentSummary } from "@/types/concept";

type FormState = {
  agent_id: string;
  name: string;
  agent_type: string;
  description: string;
  capabilities: string;
  is_active: boolean;
};

const columns: GridColDef[] = [
  { field: "agent_id", headerName: "Agent ID", minWidth: 200, flex: 1 },
  { field: "name", headerName: "Name", minWidth: 180, flex: 1 },
  { field: "agent_type", headerName: "Type", minWidth: 120, flex: 0.8 },
  { field: "is_active", headerName: "활성", width: 100, renderCell: (params) => (params.value ? "Y" : "N") },
];

const emptyForm: FormState = {
  agent_id: "",
  name: "",
  agent_type: "",
  description: "",
  capabilities: "",
  is_active: true,
};

function toForm(agent: AgentSummary): FormState {
  return {
    agent_id: agent.agent_id,
    name: agent.name,
    agent_type: agent.agent_type,
    description: agent.description ?? "",
    capabilities: Array.isArray(agent.capabilities) ? agent.capabilities.join(", ") : "",
    is_active: agent.is_active,
  };
}

function toPayload(form: FormState) {
  return {
    agent_id: form.agent_id.trim(),
    name: form.name.trim(),
    agent_type: form.agent_type.trim(),
    description: form.description.trim() || null,
    capabilities: form.capabilities
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    is_active: form.is_active,
  };
}

export default function AdminAgentsPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const agentsQuery = useQuery({
    queryKey: ["agent-catalog"],
    queryFn: () => apiGet<AgentSummary[]>("/api/v1/agents/catalog"),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toPayload(form);
      if (mode === "create") {
        return apiPost<AgentSummary>("/api/v1/agents/catalog", payload);
      }
      return apiPut<AgentSummary>(`/api/v1/agents/catalog/${selectedAgentId ?? form.agent_id}`, payload);
    },
    onSuccess: () => {
      setMessage(mode === "create" ? "Agent가 등록되었습니다." : "Agent가 수정되었습니다.");
      setError(null);
      setForm(emptyForm);
      setSelectedAgentId(null);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["agent-catalog"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "Agent 저장 중 오류가 발생했습니다.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => apiDelete<void>(`/api/v1/agents/catalog/${selectedAgentId}`),
    onSuccess: () => {
      setMessage("Agent가 삭제되었습니다.");
      setError(null);
      setForm(emptyForm);
      setSelectedAgentId(null);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["agent-catalog"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "Agent 삭제 중 오류가 발생했습니다.");
    },
  });

  const rows = useMemo(() => (agentsQuery.data ?? []).map((item) => ({ id: item.agent_id, ...item })), [agentsQuery.data]);

  function handleRowClick(params: GridRowParams) {
    const agent = params.row as AgentSummary & { id: string };
    setSelectedAgentId(agent.agent_id);
    setForm(toForm(agent));
    setMode("edit");
    setMessage(null);
    setError(null);
  }

  return (
    <AppShell title="Agent Catalog 관리">
      <Stack spacing={2}>
        {message ? <Alert severity="success">{message}</Alert> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.2fr) minmax(360px, 0.8fr)" } }}>
          <BaseDataGrid rows={rows} columns={columns} height={560} onRowClick={handleRowClick} />
          <PageCard
            title={mode === "create" ? "신규 Agent 등록" : "Agent 수정"}
            subtitle="운영 메타데이터 차원의 agent catalog를 직접 관리합니다."
          >
            <Stack spacing={2}>
              <TextField label="Agent ID" value={form.agent_id} disabled={mode === "edit"} onChange={(event) => setForm((current) => ({ ...current, agent_id: event.target.value }))} />
              <TextField label="Name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
              <TextField label="Type" value={form.agent_type} onChange={(event) => setForm((current) => ({ ...current, agent_type: event.target.value }))} />
              <TextField label="Description" multiline minRows={3} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
              <TextField label="Capabilities" value={form.capabilities} onChange={(event) => setForm((current) => ({ ...current, capabilities: event.target.value }))} />
              <FormControlLabel control={<Switch checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} />} label="활성 여부" />
              <Stack direction="row" spacing={1.5}>
                <Button variant="contained" startIcon={<SaveRoundedIcon />} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                  {mode === "create" ? "등록" : "수정"}
                </Button>
                {mode === "edit" ? (
                  <Button color="error" variant="outlined" startIcon={<DeleteOutlineRoundedIcon />} onClick={() => {
                    if (window.confirm("선택한 agent를 삭제할까요?")) {
                      deleteMutation.mutate();
                    }
                  }} disabled={deleteMutation.isPending}>
                    삭제
                  </Button>
                ) : null}
                <Button variant="outlined" onClick={() => { setForm(emptyForm); setMode("create"); setSelectedAgentId(null); }}>
                  신규
                </Button>
              </Stack>
            </Stack>
          </PageCard>
        </Box>
      </Stack>
    </AppShell>
  );
}
