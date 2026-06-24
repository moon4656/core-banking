"use client";

import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import RemoveCircleRoundedIcon from "@mui/icons-material/RemoveCircleRounded";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  FormLabel,
  IconButton,
  Radio,
  RadioGroup,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { DecisionGraphResponse, saveDecisionReview } from "@/lib/api";

type ReviewData = DecisionGraphResponse["review"];

export type ReviewDialogProps = {
  open: boolean;
  onClose: () => void;
  requestId: string;
  existing: ReviewData;
};

type FormState = {
  overall_result: string;
  intent_correct: boolean;
  concept_complete: boolean;
  agent_correct: boolean;
  evidence_sufficient: boolean;
  answer_appropriate: boolean;
  missing_concepts_text: string;
  wrong_agents_text: string;
  comment: string;
};

function initForm(existing: ReviewData): FormState {
  return {
    overall_result: existing.overall_result ?? "CORRECT",
    intent_correct: existing.intent_correct ?? true,
    concept_complete: existing.concept_complete ?? true,
    agent_correct: existing.agent_correct ?? true,
    evidence_sufficient: existing.evidence_sufficient ?? true,
    answer_appropriate: existing.answer_appropriate ?? true,
    missing_concepts_text: (existing.missing_concepts ?? []).join(", "),
    wrong_agents_text: (existing.wrong_agents ?? []).join(", "),
    comment: existing.comment ?? "",
  };
}

const RESULT_OPTIONS: { value: string; label: string; color: "success" | "warning" | "error" }[] = [
  { value: "CORRECT", label: "정확", color: "success" },
  { value: "PARTIAL", label: "부분 정확", color: "warning" },
  { value: "INCORRECT", label: "부정확", color: "error" },
];

const BOOL_FIELDS: Array<{ key: keyof FormState; label: string }> = [
  { key: "intent_correct", label: "의도 분류 정확" },
  { key: "concept_complete", label: "Concept 누락 없음" },
  { key: "agent_correct", label: "Agent 선택 정확" },
  { key: "evidence_sufficient", label: "Evidence 충분" },
  { key: "answer_appropriate", label: "최종 답변 적절" },
];

function ResultIcon({ value }: { value: string }) {
  if (value === "CORRECT") {
    return <CheckCircleRoundedIcon sx={{ fontSize: 18, color: "success.main" }} />;
  }
  if (value === "PARTIAL") {
    return <RemoveCircleRoundedIcon sx={{ fontSize: 18, color: "warning.main" }} />;
  }
  return <ErrorRoundedIcon sx={{ fontSize: 18, color: "error.main" }} />;
}

export function ReviewDialog({ open, onClose, requestId, existing }: ReviewDialogProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(() => initForm(existing));

  useEffect(() => {
    setForm(initForm(existing));
  }, [existing]);

  const mutation = useMutation({
    mutationFn: () =>
      saveDecisionReview(requestId, {
        overall_result: form.overall_result,
        intent_correct: form.intent_correct,
        concept_complete: form.concept_complete,
        agent_correct: form.agent_correct,
        evidence_sufficient: form.evidence_sufficient,
        answer_appropriate: form.answer_appropriate,
        missing_concepts: form.missing_concepts_text
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        wrong_agents: form.wrong_agents_text
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        comment: form.comment || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decision-graph", requestId] });
      onClose();
    },
  });

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const isExisting = existing.status !== "PENDING";

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1, pb: 1 }}>
        <Typography fontWeight={700} sx={{ flex: 1 }}>
          {isExisting ? "리뷰 수정" : "Decision Graph 평가"}
        </Typography>
        {isExisting ? (
          <Chip
            label={existing.status === "APPROVED" ? "승인" : "반려"}
            color={existing.status === "APPROVED" ? "success" : "error"}
            size="small"
          />
        ) : null}
        <IconButton size="small" onClick={onClose}>
          <CloseRoundedIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ pt: 2 }}>
        <Stack spacing={2.5}>
          <Box>
            <FormLabel sx={{ fontSize: 13, fontWeight: 600, mb: 0.75, display: "block" }}>
              전체 판정
            </FormLabel>
            <RadioGroup
              row
              value={form.overall_result}
              onChange={(event) => setField("overall_result", event.target.value)}
            >
              {RESULT_OPTIONS.map((option) => (
                <FormControlLabel
                  key={option.value}
                  value={option.value}
                  control={<Radio size="small" />}
                  label={
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                      <ResultIcon value={option.value} />
                      <Typography variant="body2">{option.label}</Typography>
                    </Box>
                  }
                />
              ))}
            </RadioGroup>
          </Box>

          <Divider />

          <Box>
            <FormLabel sx={{ fontSize: 13, fontWeight: 600, mb: 0.75, display: "block" }}>
              세부 항목
            </FormLabel>
            <Stack spacing={0.25}>
              {BOOL_FIELDS.map(({ key, label }) => (
                <FormControlLabel
                  key={key}
                  control={
                    <Switch
                      size="small"
                      checked={form[key] as boolean}
                      onChange={(event) => setField(key, event.target.checked as FormState[typeof key])}
                    />
                  }
                  label={<Typography variant="body2">{label}</Typography>}
                />
              ))}
            </Stack>
          </Box>

          <Divider />

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <TextField
              label="누락된 Concept"
              value={form.missing_concepts_text}
              onChange={(event) => setField("missing_concepts_text", event.target.value)}
              size="small"
              fullWidth
              placeholder="쉼표로 구분 (예: CONCEPT_INTEREST_RATE)"
            />
            <TextField
              label="잘못된 Agent"
              value={form.wrong_agents_text}
              onChange={(event) => setField("wrong_agents_text", event.target.value)}
              size="small"
              fullWidth
              placeholder="쉼표로 구분 (예: RATE_AGENT)"
            />
          </Stack>

          <TextField
            label="평가 코멘트"
            value={form.comment}
            onChange={(event) => setField("comment", event.target.value)}
            multiline
            rows={3}
            size="small"
            fullWidth
            placeholder="추가 의견이 있으면 입력하세요."
          />

          {mutation.isError ? (
            <Typography variant="caption" color="error">
              저장 실패: {(mutation.error as Error)?.message}
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} size="small">
          취소
        </Button>
        <Button
          variant="contained"
          size="small"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={14} /> : undefined}
        >
          {isExisting ? "수정 저장" : "평가 저장"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
