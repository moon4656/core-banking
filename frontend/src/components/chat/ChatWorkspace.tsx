"use client";

import AddRoundedIcon from "@mui/icons-material/AddRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import BiotechRoundedIcon from "@mui/icons-material/BiotechRounded";
import HistoryEduRoundedIcon from "@mui/icons-material/HistoryEduRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  List,
  ListItemButton,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useRef, useState } from "react";

import { MarkdownMessage } from "@/components/chat/MarkdownMessage";
import { RunResult, ScenarioPanel, scoreScenario } from "@/components/chat/ScenarioPanel";
import {
  buildSessionTitle,
  ChatSession,
  createChatSession,
  loadChatSessions,
  saveChatSessions,
} from "@/components/chat/chatSessionStorage";
import { PageCard } from "@/components/common/PageCard";
import { ApiError, apiPost } from "@/lib/api";
import { Scenario } from "@/lib/scenarios";
import { getStoredSession } from "@/lib/session";
import { ChatResponse } from "@/types/chat";

const SUGGESTED_PROMPTS = [
  "신용대출 금리와 필요서류를 함께 알려줘",
  "개인신용대출 조건과 금리 범위를 비교해줘",
  "대출 신청 전에 유의사항을 먼저 정리해줘",
];

function createMessageId(sessionId: string, role: "user" | "assistant", createdAt: number) {
  return `${sessionId}-${role}-${createdAt}`;
}

function formatSessionCount(session: ChatSession) {
  return session.messages.filter((message) => message.role === "user").length;
}

export function ChatWorkspace() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);

  // 시나리오 테스트 상태
  const [rightTab, setRightTab] = useState<"analysis" | "scenario">("analysis");
  const [runningScenarioId, setRunningScenarioId] = useState<string | null>(null);
  const [lastRunResult, setLastRunResult] = useState<RunResult | null>(null);

  const currentUserName = useMemo(() => getStoredSession()?.name ?? "portal-user", []);

  useEffect(() => {
    const restoredSessions = loadChatSessions(currentUserName);
    setSessions(restoredSessions);
    setSelectedSessionId(restoredSessions[0]?.id ?? null);
  }, [currentUserName]);

  useEffect(() => {
    saveChatSessions(currentUserName, sessions);
  }, [currentUserName, sessions]);

  const currentSession = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [selectedSessionId, sessions]
  );
  const result = currentSession?.lastResult ?? null;
  const hasMessages = Boolean(currentSession && currentSession.messages.length > 0);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [currentSession?.messages.length, loading]);

  function updateSessions(updatedSession: ChatSession) {
    setSessions((current) =>
      (current.some((session) => session.id === updatedSession.id)
        ? current.map((session) => (session.id === updatedSession.id ? updatedSession : session))
        : [updatedSession, ...current]
      ).sort((left, right) => right.updatedAt - left.updatedAt)
    );
  }

  function ensureSession() {
    if (currentSession) {
      return currentSession;
    }

    const newSession = createChatSession();
    setSessions((current) => [newSession, ...current]);
    setSelectedSessionId(newSession.id);
    return newSession;
  }

  function handleCreateSession() {
    const newSession = createChatSession();
    setSessions((current) => [newSession, ...current]);
    setSelectedSessionId(newSession.id);
    setInput("");
    setError(null);
  }

  async function handleSend() {
    if (!input.trim() || loading) {
      return;
    }

    const session = ensureSession();
    const userMessage = input.trim();
    const userCreatedAt = Date.now();
    const sessionAfterUserMessage: ChatSession = {
      ...session,
      title: session.messages.length === 0 ? buildSessionTitle(userMessage) : session.title,
      messages: [
        ...session.messages,
        {
          id: createMessageId(session.id, "user", userCreatedAt),
          role: "user",
          text: userMessage,
          createdAt: userCreatedAt,
        },
      ],
      updatedAt: userCreatedAt,
    };

    updateSessions(sessionAfterUserMessage);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await apiPost<ChatResponse>("/api/v1/ai/chat", {
        message: userMessage,
        session_id: session.id,
        channel: "web",
      });

      const assistantCreatedAt = Date.now();
      updateSessions({
        ...sessionAfterUserMessage,
        messages: [
          ...sessionAfterUserMessage.messages,
          {
            id: createMessageId(session.id, "assistant", assistantCreatedAt),
            role: "assistant",
            text: response.answer,
            createdAt: assistantCreatedAt,
          },
        ],
        lastResult: response,
        updatedAt: assistantCreatedAt,
      });
    } catch (caught) {
      const detail =
        caught instanceof ApiError ? caught.detail : "채팅 요청 처리 중 오류가 발생했습니다.";
      const assistantCreatedAt = Date.now();

      setError(detail);
      updateSessions({
        ...sessionAfterUserMessage,
        messages: [
          ...sessionAfterUserMessage.messages,
          {
            id: createMessageId(session.id, "assistant", assistantCreatedAt),
            role: "assistant",
            text: `오류가 발생했습니다.\n${detail}`,
            createdAt: assistantCreatedAt,
          },
        ],
        updatedAt: assistantCreatedAt,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleRunScenario(scenario: Scenario) {
    setRunningScenarioId(scenario.id);
    setRightTab("analysis");

    const session = ensureSession();
    const userCreatedAt = Date.now();
    const sessionAfterUserMessage: ChatSession = {
      ...session,
      title: session.messages.length === 0 ? buildSessionTitle(scenario.question) : session.title,
      messages: [
        ...session.messages,
        {
          id: createMessageId(session.id, "user", userCreatedAt),
          role: "user",
          text: `[시나리오 ${scenario.id}] ${scenario.question}`,
          createdAt: userCreatedAt,
        },
      ],
      updatedAt: userCreatedAt,
    };

    updateSessions(sessionAfterUserMessage);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await apiPost<ChatResponse>("/api/v1/ai/chat", {
        message: scenario.question,
        session_id: session.id,
        channel: "web",
      });

      const assistantCreatedAt = Date.now();
      updateSessions({
        ...sessionAfterUserMessage,
        messages: [
          ...sessionAfterUserMessage.messages,
          {
            id: createMessageId(session.id, "assistant", assistantCreatedAt),
            role: "assistant",
            text: response.answer,
            createdAt: assistantCreatedAt,
          },
        ],
        lastResult: response,
        updatedAt: assistantCreatedAt,
      });

      // 채점
      const dims = scoreScenario(scenario, response);
      setLastRunResult({
        scenarioId: scenario.id,
        dims,
        passed: dims.every((d) => d.passed),
      });
      setRightTab("scenario");
    } catch (caught) {
      const detail =
        caught instanceof ApiError ? caught.detail : "채팅 요청 처리 중 오류가 발생했습니다.";
      setError(detail);
    } finally {
      setLoading(false);
      setRunningScenarioId(null);
    }
  }

  return (
    <Box
      sx={{
        display: "grid",
        gap: { xs: 2, xl: 2.5 },
        gridTemplateColumns: {
          xs: "1fr",
          xl: "260px minmax(0, 1fr) 300px",
        },
        alignItems: "start",
      }}
    >
      <PageCard title="대화" subtitle="저장된 상담 세션">
        <Stack spacing={1.5}>
          <Button
            fullWidth
            variant="contained"
            startIcon={<AddRoundedIcon />}
            onClick={handleCreateSession}
            sx={{
              borderRadius: "16px",
              justifyContent: "flex-start",
              backgroundColor: "#111827",
              "&:hover": {
                backgroundColor: "#1f2937",
              },
            }}
          >
            새 대화
          </Button>

          <List dense sx={{ display: "grid", gap: 0.75 }}>
            {sessions.length === 0 ? (
              <Box sx={{ px: 0.5, py: 1.5 }}>
                <Typography fontWeight={600}>아직 저장된 대화가 없습니다.</Typography>
                <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
                  새 대화를 시작하면 이 목록에 세션이 저장됩니다.
                </Typography>
              </Box>
            ) : (
              sessions.map((session) => {
                const selected = session.id === selectedSessionId;

                return (
                  <ListItemButton
                    key={session.id}
                    selected={selected}
                    onClick={() => {
                      setSelectedSessionId(session.id);
                      setError(null);
                    }}
                    sx={{
                      px: 1.25,
                      py: 1.1,
                      borderRadius: "16px",
                      alignItems: "flex-start",
                      border: "1px solid",
                      borderColor: selected ? "#d1d5db" : "transparent",
                      backgroundColor: selected ? "#f3f4f6" : "transparent",
                    }}
                  >
                    <Box sx={{ width: "100%" }}>
                      <Typography
                        fontWeight={600}
                        sx={{
                          lineHeight: 1.45,
                          display: "-webkit-box",
                          WebkitBoxOrient: "vertical",
                          WebkitLineClamp: 2,
                          overflow: "hidden",
                        }}
                      >
                        {session.title}
                      </Typography>
                      <Typography color="text.secondary" variant="caption" sx={{ display: "block", mt: 0.6 }}>
                        질문 {formatSessionCount(session)}건
                      </Typography>
                    </Box>
                  </ListItemButton>
                );
              })
            )}
          </List>
        </Stack>
      </PageCard>

      <Box
        sx={{
          height: { xs: "calc(100vh - 180px)", xl: "calc(100vh - 120px)" },
          display: "flex",
          flexDirection: "column",
          borderRadius: "24px",
          backgroundColor: "#ffffff",
          border: "1px solid",
          borderColor: "divider",
          boxShadow: "0 1px 2px rgba(17, 24, 39, 0.04)",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            px: { xs: 2, md: 3 },
            py: 1.5,
            borderBottom: "1px solid",
            borderColor: "divider",
            backgroundColor: "#ffffff",
          }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            AI 상담
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.4, fontSize: 13 }}>
            상품, 금리, 서류, 규정을 대화형으로 확인하세요
          </Typography>
        </Box>

        <Box
          ref={messagesContainerRef}
          sx={{
            flex: 1,
            overflowY: "auto",
            minHeight: 0,
            px: { xs: 2, md: 4 },
            py: { xs: 2, md: 3 },
            backgroundColor: "#ffffff",
          }}
        >
          {!hasMessages ? (
            <Stack
              spacing={2.5}
              justifyContent="center"
              alignItems="center"
              sx={{ minHeight: 420, textAlign: "center" }}
            >
              <Chip
                icon={<AutoAwesomeRoundedIcon />}
                label="AI 상담 준비 완료"
                variant="outlined"
                color="primary"
              />
              <Typography variant="h4" sx={{ maxWidth: 560 }}>
                무엇을 도와드릴까요?
              </Typography>
              <Typography color="text.secondary" sx={{ maxWidth: 620, lineHeight: 1.7 }}>
                상품 정보, 금리, 필요 서류, 신청 전 유의사항까지 한 번에 정리해 드릴 수 있습니다.
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap justifyContent="center">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <Chip
                    key={prompt}
                    label={prompt}
                    variant="outlined"
                    onClick={() => setInput(prompt)}
                    sx={{
                      borderColor: "#d1d5db",
                      backgroundColor: "#f9fafb",
                    }}
                  />
                ))}
              </Stack>
            </Stack>
          ) : (
            <Stack spacing={3}>
              {currentSession?.messages.map((message) => (
                <Box
                  key={message.id}
                  sx={{
                    display: "flex",
                    justifyContent: message.role === "user" ? "flex-end" : "flex-start",
                  }}
                >
                  {message.role === "assistant" ? (
                    <Box
                      sx={{
                        width: "100%",
                        maxWidth: 820,
                        px: { xs: 0, md: 1 },
                        py: 0.25,
                      }}
                    >
                      <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 1 }}>
                        <Box
                          sx={{
                            width: 28,
                            height: 28,
                            borderRadius: "50%",
                            display: "grid",
                            placeItems: "center",
                            backgroundColor: "#e5efff",
                            color: "#1d4ed8",
                          }}
                        >
                          <AutoAwesomeRoundedIcon sx={{ fontSize: 16 }} />
                        </Box>
                        <Typography variant="subtitle2">AI 상담 도우미</Typography>
                      </Stack>
                      <MarkdownMessage content={message.text} />
                    </Box>
                  ) : (
                    <Box
                      sx={{
                        maxWidth: { xs: "92%", md: "78%" },
                        px: 2,
                        py: 1.4,
                        borderRadius: "18px",
                        backgroundColor: "#2f2f33",
                        color: "#ffffff",
                      }}
                    >
                      <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
                        {message.text}
                      </Typography>
                    </Box>
                  )}
                </Box>
              ))}

              {loading ? (
                <Box
                  sx={{
                    maxWidth: 360,
                    px: 1,
                    py: 0.5,
                  }}
                >
                  <Stack direction="row" spacing={1.25} alignItems="center">
                    <CircularProgress size={18} />
                    <Typography color="text.secondary" variant="body2">
                      답변을 준비하고 있습니다.
                    </Typography>
                  </Stack>
                </Box>
              ) : null}
            </Stack>
          )}
        </Box>

        {error ? <Alert severity="error" sx={{ mx: 2, mt: 0.5 }}>{error}</Alert> : null}

        <Box
          sx={{
            px: { xs: 2, md: 3 },
            py: 2,
            borderTop: "1px solid",
            borderColor: "divider",
            backgroundColor: "#ffffff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1.5,
              py: 1,
              borderRadius: "18px",
              border: "1px solid",
              borderColor: "#d1d5db",
              backgroundColor: "#ffffff",
              boxShadow: "0 8px 30px rgba(17, 24, 39, 0.06)",
            }}
          >
            <TextField
              fullWidth
              placeholder="메시지를 입력하세요"
              value={input}
              multiline
              minRows={1}
              maxRows={8}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void handleSend();
                }
              }}
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: "14px",
                  backgroundColor: "transparent",
                  "& fieldset": {
                    border: "none",
                  },
                },
                "& textarea": {
                  paddingTop: "6px",
                  paddingBottom: "6px",
                },
              }}
            />
            <IconButton
              aria-label="전송"
              onClick={() => void handleSend()}
              disabled={loading || !input.trim()}
              sx={{
                width: 36,
                height: 36,
                flexShrink: 0,
                borderRadius: "50%",
                color: "#ffffff",
                backgroundColor: loading || !input.trim() ? "#9ca3af" : "#111827",
                "&:hover": {
                  backgroundColor: loading || !input.trim() ? "#9ca3af" : "#1f2937",
                },
              }}
            >
              {loading ? <CircularProgress size={16} color="inherit" /> : <SendRoundedIcon sx={{ fontSize: 18 }} />}
            </IconButton>
          </Box>
          <Typography color="text.secondary" variant="caption" sx={{ display: "block", mt: 1.2, px: 0.5 }}>
            Enter로 전송, Shift+Enter로 줄바꿈
          </Typography>
        </Box>
      </Box>

      <Box
        sx={{
          borderRadius: "24px",
          backgroundColor: "#ffffff",
          border: "1px solid",
          borderColor: "divider",
          boxShadow: "0 1px 2px rgba(17, 24, 39, 0.04)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          maxHeight: { xl: "calc(100vh - 120px)" },
        }}
      >
        {/* 탭 헤더 */}
        <Tabs
          value={rightTab}
          onChange={(_, v) => setRightTab(v as "analysis" | "scenario")}
          variant="fullWidth"
          sx={{
            borderBottom: "1px solid",
            borderColor: "divider",
            minHeight: 44,
            "& .MuiTab-root": { minHeight: 44, fontSize: 13, fontWeight: 600 },
          }}
        >
          <Tab
            value="analysis"
            label="분석 근거"
            icon={<HistoryEduRoundedIcon sx={{ fontSize: 16 }} />}
            iconPosition="start"
          />
          <Tab
            value="scenario"
            label="시나리오"
            icon={<BiotechRoundedIcon sx={{ fontSize: 16 }} />}
            iconPosition="start"
          />
        </Tabs>

        {/* 탭 콘텐츠 */}
        <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
          {rightTab === "analysis" ? (
            result ? (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Request ID</Typography>
                  <Typography sx={{ mt: 0.5, wordBreak: "break-all", fontSize: 12 }}>{result.request_id}</Typography>
                </Box>
                <Divider />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>감지 Concept</Typography>
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {result.plan.detected_concepts.map((concept) => (
                      <Chip key={concept} label={concept.replace("CONCEPT_", "")} size="small" />
                    ))}
                  </Stack>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>선택 Agent</Typography>
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {result.plan.routed_agents.map((agent) => (
                      <Chip key={agent} color="primary" variant="outlined" size="small" label={agent} />
                    ))}
                  </Stack>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Trace / Evidence</Typography>
                  <Typography sx={{ mt: 0.5 }}>
                    {result.trace_count} events / {result.evidence_count} evidence
                  </Typography>
                </Box>
              </Stack>
            ) : (
              <Stack spacing={1.5}>
                <Chip
                  icon={<HistoryEduRoundedIcon />}
                  label="분석 대기"
                  variant="outlined"
                  sx={{ alignSelf: "flex-start" }}
                />
                <Typography color="text.secondary">
                  대화를 시작하면 concept, agent, trace 요약이 이 패널에 표시됩니다.
                </Typography>
              </Stack>
            )
          ) : (
            <ScenarioPanel
              runningId={runningScenarioId}
              lastResult={lastRunResult}
              onRun={handleRunScenario}
            />
          )}
        </Box>
      </Box>
    </Box>
  );
}
