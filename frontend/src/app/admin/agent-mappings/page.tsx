"use client";

import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import {
  Alert,
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GridColDef, GridRowParams } from "@mui/x-data-grid";
import { useMemo, useState } from "react";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { apiDelete, apiGet, apiPost, apiPut, ApiError } from "@/lib/api";
import { AgentMappingItem, AgentSummary, Concept } from "@/types/concept";

type FormState = {
  id: number | null;
  agent_id: string;
  concept_id: string;
  priority: string;
};

const columns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 90 },
  { field: "agent_id", headerName: "Agent", minWidth: 200, flex: 1 },
  { field: "concept_id", headerName: "Concept", minWidth: 220, flex: 1 },
  { field: "priority", headerName: "Priority", width: 100 },
];

const emptyForm: FormState = {
  id: null,
  agent_id: "",
  concept_id: "",
  priority: "0",
};

export default function AdminAgentMappingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const agentsQuery = useQuery({
    queryKey: ["admin-agents"],
    queryFn: () => apiGet<AgentSummary[]>("/api/v1/agents"),
  });

  const conceptsQuery = useQuery({
    queryKey: ["admin-agent-mapping-concepts"],
    queryFn: () => apiGet<Concept[]>("/api/v1/knowledge/concepts"),
  });

  const mappingsQuery = useQuery({
    queryKey: ["agent-mappings"],
    queryFn: () => apiGet<AgentMappingItem[]>("/api/v1/knowledge/agent-mappings"),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        agent_id: form.agent_id,
        concept_id: form.concept_id,
        priority: Number(form.priority),
      };
      if (mode === "create") {
        return apiPost<AgentMappingItem>("/api/v1/knowledge/agent-mappings", payload);
      }
      return apiPut<AgentMappingItem>(`/api/v1/knowledge/agent-mappings/${form.id}`, payload);
    },
    onSuccess: () => {
      setMessage(mode === "create" ? "Agent 매핑이 등록되었습니다." : "Agent 매핑이 수정되었습니다.");
      setError(null);
      setForm(emptyForm);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["agent-mappings"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "Agent 매핑 저장 중 오류가 발생했습니다.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => apiDelete<void>(`/api/v1/knowledge/agent-mappings/${form.id}`),
    onSuccess: () => {
      setMessage("Agent 매핑이 삭제되었습니다.");
      setError(null);
      setForm(emptyForm);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["agent-mappings"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "Agent 매핑 삭제 중 오류가 발생했습니다.");
    },
  });

  const rows = useMemo(() => mappingsQuery.data ?? [], [mappingsQuery.data]);

  function handleRowClick(params: GridRowParams) {
    setForm({
      id: Number(params.row.id),
      agent_id: String(params.row.agent_id),
      concept_id: String(params.row.concept_id),
      priority: String(params.row.priority),
    });
    setMode("edit");
    setMessage(null);
    setError(null);
  }

  return (
    <AppShell title="Agent 매핑 관리">
      <Stack spacing={2}>
        {message ? <Alert severity="success">{message}</Alert> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.2fr) minmax(360px, 0.8fr)" } }}>
          <BaseDataGrid rows={rows} columns={columns} height={560} onRowClick={handleRowClick} />

          <PageCard
            title={mode === "create" ? "신규 Agent 매핑 등록" : "Agent 매핑 수정"}
            subtitle="업무 concept를 어떤 agent가 처리할지 운영자가 직접 제어합니다."
          >
            <Stack spacing={2}>
              <TextField
                select
                label="Agent"
                value={form.agent_id}
                onChange={(event) => setForm((current) => ({ ...current, agent_id: event.target.value }))}
              >
                {(agentsQuery.data ?? []).map((agent) => (
                  <MenuItem key={agent.agent_id} value={agent.agent_id}>
                    {agent.agent_id}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Concept"
                value={form.concept_id}
                onChange={(event) => setForm((current) => ({ ...current, concept_id: event.target.value }))}
              >
                {(conceptsQuery.data ?? []).map((concept) => (
                  <MenuItem key={concept.concept_id} value={concept.concept_id}>
                    {concept.concept_id}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Priority"
                value={form.priority}
                onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}
              />
              <Stack direction="row" spacing={1.5}>
                <Button variant="contained" startIcon={<SaveRoundedIcon />} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                  {mode === "create" ? "등록" : "수정"}
                </Button>
                {mode === "edit" ? (
                  <Button
                    color="error"
                    variant="outlined"
                    startIcon={<DeleteOutlineRoundedIcon />}
                    onClick={() => {
                      if (window.confirm("선택한 agent mapping을 삭제할까요?")) {
                        deleteMutation.mutate();
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    삭제
                  </Button>
                ) : null}
                <Button variant="outlined" onClick={() => { setForm(emptyForm); setMode("create"); }}>
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
