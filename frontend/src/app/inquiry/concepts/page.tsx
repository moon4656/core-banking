"use client";

import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { GridColDef } from "@mui/x-data-grid";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageCard } from "@/components/common/PageCard";
import { BaseDataGrid } from "@/components/grid/BaseDataGrid";
import { AppShell } from "@/components/layout/AppShell";
import { apiGet, ApiError } from "@/lib/api";
import { Concept, ConceptDetail } from "@/types/concept";

const columns: GridColDef[] = [
  { field: "concept_id", headerName: "Concept ID", minWidth: 220, flex: 1 },
  { field: "name", headerName: "이름", minWidth: 180, flex: 1 },
  { field: "domain", headerName: "도메인", minWidth: 140, flex: 0.8 },
  {
    field: "is_active",
    headerName: "활성",
    minWidth: 110,
    renderCell: (params) => (params.value ? "Y" : "N"),
  },
];

type ConceptRow = {
  id: string;
  concept_id: string;
  name: string;
  description: string | null;
  domain: string | null;
  is_active: boolean;
  aliases: string[];
};

function hasAliases(item: Concept | ConceptDetail): item is ConceptDetail {
  return Array.isArray((item as ConceptDetail).aliases);
}

export default function ConceptInquiryPage() {
  const [keyword, setKeyword] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");

  const conceptQuery = useQuery({
    queryKey: ["concepts", searchKeyword],
    queryFn: () =>
      searchKeyword
        ? apiGet<ConceptDetail[]>(
            `/api/v1/knowledge/concepts/search?keyword=${encodeURIComponent(searchKeyword)}`
          )
        : apiGet<Concept[]>("/api/v1/knowledge/concepts"),
  });

  const rows: ConceptRow[] = (conceptQuery.data ?? []).map((item) => ({
    id: item.concept_id,
    ...item,
    aliases: hasAliases(item) ? item.aliases : [],
  }));

  const selectedRow = rows[0];
  const errorMessage =
    conceptQuery.error instanceof ApiError ? conceptQuery.error.detail : null;

  return (
    <AppShell title="기준정보 조회">
      <Stack spacing={2}>
        <PageCard
          title="개념 조회"
          subtitle="업무 개념, 도메인, 별칭을 검색해서 마스터성 정보를 빠르게 확인합니다."
        >
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField
              fullWidth
              label="검색어"
              placeholder="예: 금리, 대출, 서류"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <Button
              variant="contained"
              startIcon={<SearchRoundedIcon />}
              onClick={() => setSearchKeyword(keyword.trim())}
            >
              조회
            </Button>
            <Button variant="outlined" onClick={() => {
              setKeyword("");
              setSearchKeyword("");
            }}>
              전체
            </Button>
          </Stack>
        </PageCard>

        {errorMessage ? <Alert severity="error">{errorMessage}</Alert> : null}

        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1.4fr) minmax(320px, 0.6fr)" },
          }}
        >
          <BaseDataGrid rows={rows} columns={columns} />

          <PageCard
            title="상세 미리보기"
            subtitle="1차 버전은 첫 번째 조회 결과를 기준으로 상세 정보를 보여줍니다."
          >
            {selectedRow ? (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Concept ID
                  </Typography>
                  <Typography>{selectedRow.concept_id}</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    설명
                  </Typography>
                  <Typography>{selectedRow.description ?? "-"}</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    별칭
                  </Typography>
                  <Stack direction="row" gap={1} flexWrap="wrap">
                    {selectedRow.aliases.length > 0 ? (
                      selectedRow.aliases.map((alias: string) => (
                        <Chip key={alias} label={alias} />
                      ))
                    ) : (
                      <Typography color="text.secondary">별칭 정보 없음</Typography>
                    )}
                  </Stack>
                </Box>
              </Stack>
            ) : (
              <Typography color="text.secondary">조회 결과가 없습니다.</Typography>
            )}
          </PageCard>
        </Box>
      </Stack>
    </AppShell>
  );
}
