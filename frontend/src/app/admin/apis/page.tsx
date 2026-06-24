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
import { ApiSummary } from "@/types/concept";

type FormState = {
  api_id: string;
  name: string;
  endpoint: string;
  method: string;
  description: string;
  is_active: boolean;
};

const columns: GridColDef[] = [
  { field: "api_id", headerName: "API ID", minWidth: 200, flex: 1 },
  { field: "name", headerName: "Name", minWidth: 180, flex: 1 },
  { field: "method", headerName: "Method", width: 100 },
  { field: "is_active", headerName: "활성", width: 100, renderCell: (params) => (params.value ? "Y" : "N") },
];

const emptyForm: FormState = {
  api_id: "",
  name: "",
  endpoint: "",
  method: "GET",
  description: "",
  is_active: true,
};

function toForm(api: ApiSummary): FormState {
  return {
    api_id: api.api_id,
    name: api.name,
    endpoint: api.endpoint,
    method: api.method,
    description: api.description ?? "",
    is_active: api.is_active,
  };
}

function toPayload(form: FormState) {
  return {
    api_id: form.api_id.trim(),
    name: form.name.trim(),
    endpoint: form.endpoint.trim(),
    method: form.method.trim(),
    description: form.description.trim() || null,
    is_active: form.is_active,
  };
}

export default function AdminApisPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [selectedApiId, setSelectedApiId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const apisQuery = useQuery({
    queryKey: ["tool-catalog"],
    queryFn: () => apiGet<ApiSummary[]>("/api/v1/tools/catalog"),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toPayload(form);
      if (mode === "create") {
        return apiPost<ApiSummary>("/api/v1/tools/catalog", payload);
      }
      return apiPut<ApiSummary>(`/api/v1/tools/catalog/${selectedApiId ?? form.api_id}`, payload);
    },
    onSuccess: () => {
      setMessage(mode === "create" ? "API가 등록되었습니다." : "API가 수정되었습니다.");
      setError(null);
      setForm(emptyForm);
      setSelectedApiId(null);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["tool-catalog"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "API 저장 중 오류가 발생했습니다.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => apiDelete<void>(`/api/v1/tools/catalog/${selectedApiId}`),
    onSuccess: () => {
      setMessage("API가 삭제되었습니다.");
      setError(null);
      setForm(emptyForm);
      setSelectedApiId(null);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["tool-catalog"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "API 삭제 중 오류가 발생했습니다.");
    },
  });

  const rows = useMemo(() => (apisQuery.data ?? []).map((item) => ({ id: item.api_id, ...item })), [apisQuery.data]);

  function handleRowClick(params: GridRowParams) {
    const api = params.row as ApiSummary & { id: string };
    setSelectedApiId(api.api_id);
    setForm(toForm(api));
    setMode("edit");
    setMessage(null);
    setError(null);
  }

  return (
    <AppShell title="API Catalog 관리">
      <Stack spacing={2}>
        {message ? <Alert severity="success">{message}</Alert> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.2fr) minmax(360px, 0.8fr)" } }}>
          <BaseDataGrid rows={rows} columns={columns} height={560} onRowClick={handleRowClick} />
          <PageCard
            title={mode === "create" ? "신규 API 등록" : "API 수정"}
            subtitle="Tool/API catalog를 운영자가 직접 유지보수할 수 있도록 연결했습니다."
          >
            <Stack spacing={2}>
              <TextField label="API ID" value={form.api_id} disabled={mode === "edit"} onChange={(event) => setForm((current) => ({ ...current, api_id: event.target.value }))} />
              <TextField label="Name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
              <TextField label="Endpoint" value={form.endpoint} onChange={(event) => setForm((current) => ({ ...current, endpoint: event.target.value }))} />
              <TextField label="Method" value={form.method} onChange={(event) => setForm((current) => ({ ...current, method: event.target.value }))} />
              <TextField label="Description" multiline minRows={3} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
              <FormControlLabel control={<Switch checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} />} label="활성 여부" />
              <Stack direction="row" spacing={1.5}>
                <Button variant="contained" startIcon={<SaveRoundedIcon />} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                  {mode === "create" ? "등록" : "수정"}
                </Button>
                {mode === "edit" ? (
                  <Button color="error" variant="outlined" startIcon={<DeleteOutlineRoundedIcon />} onClick={() => {
                    if (window.confirm("선택한 API를 삭제할까요?")) {
                      deleteMutation.mutate();
                    }
                  }} disabled={deleteMutation.isPending}>
                    삭제
                  </Button>
                ) : null}
                <Button variant="outlined" onClick={() => { setForm(emptyForm); setMode("create"); setSelectedApiId(null); }}>
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
