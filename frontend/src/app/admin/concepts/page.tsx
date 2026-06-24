"use client";

import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import {
  Alert,
  Box,
  Button,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GridColDef, GridRowParams } from "@mui/x-data-grid";
import { useEffect, useMemo, useState } from "react";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { apiDelete, apiGet, apiPost, apiPut, ApiError } from "@/lib/api";
import { Concept, ConceptDetail } from "@/types/concept";

type ConceptFormState = {
  concept_id: string;
  name: string;
  description: string;
  domain: string;
  is_active: boolean;
  aliases: string;
};

const columns: GridColDef[] = [
  { field: "concept_id", headerName: "Concept ID", minWidth: 220, flex: 1 },
  { field: "name", headerName: "이름", minWidth: 180, flex: 1 },
  { field: "domain", headerName: "도메인", minWidth: 140, flex: 0.8 },
  {
    field: "is_active",
    headerName: "활성",
    width: 100,
    renderCell: (params) => (params.value ? "Y" : "N"),
  },
];

const emptyForm: ConceptFormState = {
  concept_id: "",
  name: "",
  description: "",
  domain: "",
  is_active: true,
  aliases: "",
};

function toPayload(form: ConceptFormState) {
  return {
    concept_id: form.concept_id.trim(),
    name: form.name.trim(),
    description: form.description.trim() || null,
    domain: form.domain.trim() || null,
    is_active: form.is_active,
    aliases: form.aliases
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}

function toForm(concept: ConceptDetail): ConceptFormState {
  return {
    concept_id: concept.concept_id,
    name: concept.name,
    description: concept.description ?? "",
    domain: concept.domain ?? "",
    is_active: concept.is_active,
    aliases: concept.aliases.join(", "),
  };
}

export default function AdminConceptPage() {
  const queryClient = useQueryClient();
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);
  const [form, setForm] = useState<ConceptFormState>(emptyForm);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const conceptsQuery = useQuery({
    queryKey: ["admin-concepts"],
    queryFn: () => apiGet<Concept[]>("/api/v1/knowledge/concepts"),
  });

  const conceptDetailQuery = useQuery({
    queryKey: ["admin-concept", selectedConceptId],
    queryFn: () => apiGet<ConceptDetail>(`/api/v1/knowledge/concepts/${selectedConceptId}`),
    enabled: !!selectedConceptId,
  });

  useEffect(() => {
    if (conceptDetailQuery.data) {
      setForm(toForm(conceptDetailQuery.data));
      setMode("edit");
    }
  }, [conceptDetailQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toPayload(form);
      if (mode === "create") {
        return apiPost<ConceptDetail>("/api/v1/knowledge/concepts", payload);
      }

      return apiPut<ConceptDetail>(
        `/api/v1/knowledge/concepts/${selectedConceptId ?? form.concept_id}`,
        payload
      );
    },
    onSuccess: (data) => {
      setMessage(mode === "create" ? "개념이 등록되었습니다." : "개념이 수정되었습니다.");
      setError(null);
      setSelectedConceptId(data.concept_id);
      setForm(toForm(data));
      setMode("edit");
      void queryClient.invalidateQueries({ queryKey: ["admin-concepts"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-concept", data.concept_id] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "저장 중 오류가 발생했습니다.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const conceptId = selectedConceptId ?? form.concept_id;
      return apiDelete<void>(`/api/v1/knowledge/concepts/${conceptId}`);
    },
    onSuccess: () => {
      setMessage("개념이 삭제되었습니다.");
      setError(null);
      resetForCreate();
      void queryClient.invalidateQueries({ queryKey: ["admin-concepts"] });
    },
    onError: (caught) => {
      setMessage(null);
      setError(caught instanceof ApiError ? caught.detail : "삭제 중 오류가 발생했습니다.");
    },
  });

  const rows = useMemo(
    () =>
      (conceptsQuery.data ?? []).map((item) => ({
        id: item.concept_id,
        ...item,
      })),
    [conceptsQuery.data]
  );

  function handleRowClick(params: GridRowParams) {
    setSelectedConceptId(String(params.row.concept_id));
    setMessage(null);
    setError(null);
  }

  function resetForCreate() {
    setSelectedConceptId(null);
    setForm(emptyForm);
    setMode("create");
    setMessage(null);
    setError(null);
  }

  return (
    <AppShell title="기준정보 관리">
      <Stack spacing={2}>
        <PageCard
          title="Concept 관리"
          subtitle="관리자 화면에서 등록, 수정, 조회를 바로 수행할 수 있도록 연결했습니다."
        >
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <Button variant="outlined" onClick={resetForCreate}>
              신규 등록
            </Button>
            <Typography color="text.secondary" sx={{ alignSelf: "center" }}>
              현재 단계는 `business_concept`와 `business_term_alias`를 함께 관리합니다.
            </Typography>
          </Stack>
        </PageCard>

        {message ? <Alert severity="success">{message}</Alert> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.25fr) minmax(360px, 0.75fr)" },
          }}
        >
          <BaseDataGrid rows={rows} columns={columns} height={560} onRowClick={handleRowClick} />

          <PageCard
            title={mode === "create" ? "신규 Concept 등록" : "Concept 수정"}
            subtitle="별칭은 쉼표로 구분해서 입력합니다."
          >
            <Stack spacing={2}>
              <TextField
                label="Concept ID"
                value={form.concept_id}
                disabled={mode === "edit"}
                onChange={(event) => setForm((current) => ({ ...current, concept_id: event.target.value }))}
              />
              <TextField
                label="이름"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              />
              <TextField
                label="설명"
                multiline
                minRows={3}
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              />
              <TextField
                label="도메인"
                value={form.domain}
                onChange={(event) => setForm((current) => ({ ...current, domain: event.target.value }))}
              />
              <TextField
                label="별칭"
                value={form.aliases}
                onChange={(event) => setForm((current) => ({ ...current, aliases: event.target.value }))}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, is_active: event.target.checked }))
                    }
                  />
                }
                label="활성 여부"
              />
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
                    if (window.confirm("선택한 concept를 삭제할까요?")) {
                      deleteMutation.mutate();
                    }
                  }}
                  disabled={deleteMutation.isPending}
                >
                  삭제
                </Button>
              ) : null}
            </Stack>
          </PageCard>
        </Box>
      </Stack>
    </AppShell>
  );
}
