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
import { AliasItem, Concept } from "@/types/concept";

type AliasFormState = {
  id: number | null;
  concept_id: string;
  alias: string;
  language: string;
};

const columns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 90 },
  { field: "concept_id", headerName: "Concept ID", minWidth: 220, flex: 1 },
  { field: "alias", headerName: "Alias", minWidth: 200, flex: 1 },
  { field: "language", headerName: "Language", width: 120 },
];

const emptyForm: AliasFormState = {
  id: null,
  concept_id: "",
  alias: "",
  language: "ko",
};

export default function AdminAliasesPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AliasFormState>(emptyForm);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const conceptsQuery = useQuery({
    queryKey: ["alias-concepts"],
    queryFn: () => apiGet<Concept[]>("/api/v1/knowledge/concepts"),
  });

  const aliasesQuery = useQuery({
    queryKey: ["aliases"],
    queryFn: () => apiGet<AliasItem[]>("/api/v1/knowledge/aliases"),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return apiPost<AliasItem>("/api/v1/knowledge/aliases", {
          concept_id: form.concept_id,
          alias: form.alias,
          language: form.language,
        });
      }

      return apiPut<AliasItem>(`/api/v1/knowledge/aliases/${form.id}`, {
        alias: form.alias,
        language: form.language,
      });
    },
    onSuccess: () => {
      setMessage(mode === "create" ? "별칭이 등록되었습니다." : "별칭이 수정되었습니다.");
      setError(null);
      setForm(emptyForm);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["aliases"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "별칭 저장 중 오류가 발생했습니다.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => apiDelete<void>(`/api/v1/knowledge/aliases/${form.id}`),
    onSuccess: () => {
      setMessage("별칭이 삭제되었습니다.");
      setError(null);
      setForm(emptyForm);
      setMode("create");
      void queryClient.invalidateQueries({ queryKey: ["aliases"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "별칭 삭제 중 오류가 발생했습니다.");
    },
  });

  const rows = useMemo(() => aliasesQuery.data ?? [], [aliasesQuery.data]);

  function handleRowClick(params: GridRowParams) {
    setForm({
      id: Number(params.row.id),
      concept_id: String(params.row.concept_id),
      alias: String(params.row.alias),
      language: String(params.row.language),
    });
    setMode("edit");
    setMessage(null);
    setError(null);
  }

  return (
    <AppShell title="Alias 관리">
      <Stack spacing={2}>
        {message ? <Alert severity="success">{message}</Alert> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.2fr) minmax(360px, 0.8fr)" },
          }}
        >
          <BaseDataGrid rows={rows} columns={columns} height={560} onRowClick={handleRowClick} />

          <PageCard
            title={mode === "create" ? "신규 Alias 등록" : "Alias 수정"}
            subtitle="별칭은 특정 concept에 연결되어 검색 정확도를 높입니다."
          >
            <Stack spacing={2}>
              <TextField
                select
                label="Concept"
                value={form.concept_id}
                disabled={mode === "edit"}
                onChange={(event) =>
                  setForm((current) => ({ ...current, concept_id: event.target.value }))
                }
              >
                {(conceptsQuery.data ?? []).map((concept) => (
                  <MenuItem key={concept.concept_id} value={concept.concept_id}>
                    {concept.concept_id}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Alias"
                value={form.alias}
                onChange={(event) =>
                  setForm((current) => ({ ...current, alias: event.target.value }))
                }
              />
              <TextField
                label="Language"
                value={form.language}
                onChange={(event) =>
                  setForm((current) => ({ ...current, language: event.target.value }))
                }
              />
              <Stack direction="row" spacing={1.5}>
                <Button
                  variant="contained"
                  startIcon={<SaveRoundedIcon />}
                  onClick={() => saveMutation.mutate()}
                  disabled={saveMutation.isPending}
                >
                  {mode === "create" ? "등록" : "수정"}
                </Button>
                {mode === "edit" ? (
                  <Button
                    color="error"
                    variant="outlined"
                    startIcon={<DeleteOutlineRoundedIcon />}
                    onClick={() => {
                      if (window.confirm("선택한 alias를 삭제할까요?")) {
                        deleteMutation.mutate();
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    삭제
                  </Button>
                ) : null}
                <Button
                  variant="outlined"
                  onClick={() => {
                    setForm(emptyForm);
                    setMode("create");
                  }}
                >
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
