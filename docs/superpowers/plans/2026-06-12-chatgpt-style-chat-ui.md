# ChatGPT-Style Chat UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the authenticated frontend shell and AI chat page so the experience feels closer to ChatGPT while preserving banking-portal clarity and the evidence sidebar workflow.

**Architecture:** Keep the existing Next.js + MUI app structure, but rebalance the authenticated shell into a quieter dark sidebar, slimmer topbar, wider central conversation canvas, and lower-weight evidence panel. Rework the chat workspace markup and theme tokens rather than changing data flow, API contracts, or markdown rendering behavior.

**Tech Stack:** Next.js App Router, React 18, TypeScript, Material UI 6, local session storage, existing chat API integration

---

## File Map

- Modify: `frontend/src/lib/theme.ts`
  - Rebalance palette, shape, and typography tokens toward a restrained ChatGPT-inspired shell with banking-blue accents.
- Modify: `frontend/src/components/common/PageCard.tsx`
  - Make shared card chrome lighter and more flexible for support panels.
- Modify: `frontend/src/components/layout/AppShell.tsx`
  - Adjust authenticated page background, spacing, and shell proportions.
- Modify: `frontend/src/components/layout/Sidebar.tsx`
  - Restyle left navigation into a darker, simpler rail without removing current menu structure.
- Modify: `frontend/src/components/layout/Topbar.tsx`
  - Reduce the top header into a slimmer contextual bar with de-emphasized metadata.
- Modify: `frontend/src/components/chat/MarkdownMessage.tsx`
  - Tune markdown typography and inline code styling to fit flatter assistant responses.
- Modify: `frontend/src/components/chat/ChatWorkspace.tsx`
  - Rebuild the AI chat page layout, empty state, message presentation, suggested prompts behavior, and composer styling.

## Task 1: Refresh Theme And Shared Card Surface

**Files:**
- Modify: `frontend/src/lib/theme.ts`
- Modify: `frontend/src/components/common/PageCard.tsx`

- [ ] **Step 1: Update the global theme tokens**

Replace the theme object in `frontend/src/lib/theme.ts` with:

```ts
import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    primary: {
      main: "#2563eb",
      dark: "#1d4ed8",
      light: "#dbeafe",
    },
    secondary: {
      main: "#0f766e",
    },
    background: {
      default: "#f7f7f8",
      paper: "#ffffff",
    },
    text: {
      primary: "#111827",
      secondary: "#6b7280",
    },
    divider: "#e5e7eb",
  },
  shape: {
    borderRadius: 18,
  },
  typography: {
    fontFamily: "\"Segoe UI\", \"Noto Sans KR\", sans-serif",
    h4: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h5: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h6: {
      fontWeight: 700,
    },
    subtitle1: {
      fontWeight: 600,
    },
  },
});
```

- [ ] **Step 2: Lighten the shared card surface**

Update `frontend/src/components/common/PageCard.tsx` to:

```tsx
"use client";

import { Card, CardContent, Typography } from "@mui/material";
import { ReactNode } from "react";

export function PageCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <Card
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 5,
        backgroundColor: "background.paper",
        boxShadow: "0 1px 2px rgba(17, 24, 39, 0.04)",
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography variant="h6">{title}</Typography>
        {subtitle ? (
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2 }}>
            {subtitle}
          </Typography>
        ) : null}
        {children}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Run frontend build to catch type or theme regressions early**

Run: `npm run build`

Expected: build completes successfully.

- [ ] **Step 4: Commit the theme foundation changes**

```bash
git add frontend/src/lib/theme.ts frontend/src/components/common/PageCard.tsx
git commit -m "feat: refresh shell theme foundation"
```

## Task 2: Rework The Authenticated Shell

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/components/layout/Topbar.tsx`

- [ ] **Step 1: Update the shell spacing and background**

Change the return block in `frontend/src/components/layout/AppShell.tsx` to:

```tsx
return (
  <Box
    sx={{
      display: "flex",
      minHeight: "100vh",
      backgroundColor: "#f7f7f8",
    }}
  >
    <Sidebar />
    <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
      <Topbar title={title} />
      <Box
        component="main"
        sx={{
          flex: 1,
          px: { xs: 2, md: 3 },
          py: { xs: 2, md: 2.5 },
        }}
      >
        {children}
      </Box>
    </Box>
  </Box>
);
```

- [ ] **Step 2: Replace the sidebar surface with a darker, simpler rail**

Update the outer `Box` and menu button styles in `frontend/src/components/layout/Sidebar.tsx` with:

```tsx
<Box
  sx={{
    width: { xs: 88, md: 280 },
    minHeight: "100vh",
    px: { xs: 1.25, md: 1.75 },
    py: 2,
    display: "flex",
    flexDirection: "column",
    color: "#f3f4f6",
    backgroundColor: "#202123",
    borderRight: "1px solid rgba(255,255,255,0.06)",
  }}
>
```

Use this title block:

```tsx
<Box sx={{ px: { xs: 0.75, md: 1.25 }, mb: 2.5 }}>
  <Typography
    variant="subtitle1"
    sx={{ fontWeight: 700, color: "#f9fafb", display: { xs: "none", md: "block" } }}
  >
    Core Banking AI
  </Typography>
  <Typography
    sx={{
      mt: 0.5,
      color: "rgba(243,244,246,0.62)",
      fontSize: 13,
      display: { xs: "none", md: "block" },
    }}
  >
    Banking operations workspace
  </Typography>
</Box>
```

Use this `ListItemButton` style:

```tsx
sx={{
  minHeight: 46,
  px: { xs: 1, md: 1.25 },
  borderRadius: 3,
  color: "rgba(243,244,246,0.9)",
  "& .MuiListItemText-root": {
    display: { xs: "none", md: "block" },
  },
  "&.Mui-selected": {
    backgroundColor: "rgba(255,255,255,0.08)",
    color: "#ffffff",
  },
  "&:hover": {
    backgroundColor: "rgba(255,255,255,0.05)",
  },
}}
```

Update the account box styles to:

```tsx
sx={{
  mt: 2,
  p: { xs: 1.25, md: 1.5 },
  borderRadius: 3,
  border: "1px solid rgba(255,255,255,0.08)",
  backgroundColor: "rgba(255,255,255,0.04)",
}}
```

- [ ] **Step 3: Slim the topbar into a quieter status bar**

Replace the top-level container in `frontend/src/components/layout/Topbar.tsx` with:

```tsx
<Box
  sx={{
    px: { xs: 2, md: 3 },
    py: 1.5,
    borderBottom: "1px solid",
    borderColor: "divider",
    backgroundColor: "rgba(255,255,255,0.82)",
    backdropFilter: "blur(10px)",
    position: "sticky",
    top: 0,
    zIndex: 10,
  }}
>
```

Use a smaller heading block:

```tsx
<Box>
  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
    {title}
  </Typography>
  <Typography color="text.secondary" sx={{ mt: 0.25, fontSize: 13 }}>
    AI guidance, trace evidence, and operational context
  </Typography>
</Box>
```

Use this metadata stack wrapper:

```tsx
<Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
```

- [ ] **Step 4: Run frontend build after shell restyling**

Run: `npm run build`

Expected: build completes successfully.

- [ ] **Step 5: Commit the shell restyle**

```bash
git add frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/components/layout/Topbar.tsx
git commit -m "feat: restyle authenticated app shell"
```

## Task 3: Flatten Assistant Markdown Presentation

**Files:**
- Modify: `frontend/src/components/chat/MarkdownMessage.tsx`

- [ ] **Step 1: Update markdown spacing to fit flatter assistant responses**

Adjust the root `Box` styles in `frontend/src/components/chat/MarkdownMessage.tsx` to:

```tsx
sx={{
  lineHeight: 1.7,
  overflowWrap: "anywhere",
  color: "#1f2937",
  "& > :first-of-type": { mt: 0 },
  "& > :last-child": { mb: 0 },
  "& ul, & ol": {
    marginTop: 0.3,
    marginBottom: 0.3,
  },
  "& li > p": {
    margin: 0,
  },
}}
```

Update the markdown component styles to:

```tsx
h1: ({ children }) => (
  <Typography variant="h5" sx={{ mt: 0.5, mb: 1.5 }}>
    {children}
  </Typography>
),
h2: ({ children }) => (
  <Typography variant="h6" sx={{ mt: 0.4, mb: 1.2 }}>
    {children}
  </Typography>
),
h3: ({ children }) => (
  <Typography variant="subtitle1" sx={{ mt: 1.25, mb: 0.55, fontWeight: 700 }}>
    {children}
  </Typography>
),
p: ({ children }) => (
  <Typography sx={{ mb: 0.8, whiteSpace: "pre-wrap", color: "inherit" }}>
    {children}
  </Typography>
),
blockquote: ({ children }) => (
  <Box
    component="blockquote"
    sx={{
      my: 1.5,
      mx: 0,
      pl: 1.5,
      py: 0.1,
      borderLeft: "3px solid #d1d5db",
      color: "#4b5563",
    }}
  >
    {children}
  </Box>
),
code: ({ children }) => (
  <Box
    component="code"
    sx={{
      px: 0.65,
      py: 0.2,
      borderRadius: 1,
      fontFamily: '"JetBrains Mono", Consolas, monospace',
      fontSize: "0.9em",
      backgroundColor: "#f3f4f6",
    }}
  >
    {children}
  </Box>
),
```

- [ ] **Step 2: Run frontend build after markdown style changes**

Run: `npm run build`

Expected: build completes successfully.

- [ ] **Step 3: Commit the markdown presentation update**

```bash
git add frontend/src/components/chat/MarkdownMessage.tsx
git commit -m "feat: simplify assistant markdown presentation"
```

## Task 4: Rebuild The Chat Workspace Layout

**Files:**
- Modify: `frontend/src/components/chat/ChatWorkspace.tsx`

- [ ] **Step 1: Add layout helpers and update suggested prompts behavior**

In `frontend/src/components/chat/ChatWorkspace.tsx`, compute a boolean for whether the current session has messages:

```tsx
  const hasMessages = Boolean(currentSession && currentSession.messages.length > 0);
```

Use this prompt list:

```tsx
const SUGGESTED_PROMPTS = [
  "신용대출 금리와 필요서류를 함께 알려줘",
  "개인신용대출 조건과 금리 범위를 비교해줘",
  "대출 신청 전에 유의사항을 먼저 정리해줘",
];
```

- [ ] **Step 2: Replace the chat workspace return layout**

Replace the full `return (...)` block in `frontend/src/components/chat/ChatWorkspace.tsx` with a three-column responsive layout that uses:

```tsx
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
```

Use a lightweight conversation list panel on the left:

```tsx
<PageCard
  title="대화"
  subtitle="저장된 상담 세션"
>
```

Inside it, keep the existing session list logic, but change the new-chat button label to `새 대화` and style it with a darker filled button and flatter list items. Selected session items should use:

```tsx
sx={{
  px: 1.25,
  py: 1.1,
  borderRadius: 3,
  alignItems: "flex-start",
  border: "1px solid",
  borderColor: selected ? "#d1d5db" : "transparent",
  backgroundColor: selected ? "#f3f4f6" : "transparent",
}}
```

- [ ] **Step 3: Build the center chat column around a flatter conversation canvas**

In the center column, replace the large card title/subtitle pattern with a direct conversation workspace:

```tsx
<Box
  sx={{
    minHeight: { xs: "calc(100vh - 180px)", xl: "calc(100vh - 120px)" },
    display: "flex",
    flexDirection: "column",
    borderRadius: 6,
    backgroundColor: "#ffffff",
    border: "1px solid",
    borderColor: "divider",
    boxShadow: "0 1px 2px rgba(17, 24, 39, 0.04)",
    overflow: "hidden",
  }}
>
```

Add a slim top strip inside the chat panel:

```tsx
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
```

Use a scrollable message area:

```tsx
<Box
  sx={{
    flex: 1,
    overflowY: "auto",
    px: { xs: 2, md: 4 },
    py: { xs: 2, md: 3 },
    backgroundColor: "#ffffff",
  }}
>
```

If `!hasMessages`, render a centered welcome state with:

```tsx
<Typography variant="h4" sx={{ maxWidth: 560 }}>
  무엇을 도와드릴까요?
</Typography>
```

and only show the suggested prompt chips in this empty state.

- [ ] **Step 4: Update message row styling**

Keep the current message iteration and API behavior, but change the wrappers as follows.

For the row wrapper:

```tsx
<Box
  key={message.id}
  sx={{
    display: "flex",
    justifyContent: message.role === "user" ? "flex-end" : "flex-start",
  }}
>
```

For assistant messages:

```tsx
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
```

For user messages:

```tsx
<Box
  sx={{
    maxWidth: { xs: "92%", md: "78%" },
    px: 2,
    py: 1.4,
    borderRadius: 4,
    backgroundColor: "#2f2f33",
    color: "#ffffff",
  }}
>
  <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
    {message.text}
  </Typography>
</Box>
```

For the loading state:

```tsx
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
```

- [ ] **Step 5: Replace the composer with a bottom-fixed ChatGPT-like input**

Below the message area, use:

```tsx
<Box
  sx={{
    px: { xs: 2, md: 3 },
    py: 2,
    borderTop: "1px solid",
    borderColor: "divider",
    backgroundColor: "#ffffff",
  }}
>
```

Wrap the input and send button in:

```tsx
<Box
  sx={{
    display: "flex",
    alignItems: "flex-end",
    gap: 1,
    p: 1,
    borderRadius: 4,
    border: "1px solid",
    borderColor: "#d1d5db",
    backgroundColor: "#ffffff",
    boxShadow: "0 8px 30px rgba(17, 24, 39, 0.06)",
  }}
>
```

Set the text field style to:

```tsx
sx={{
  "& .MuiOutlinedInput-root": {
    alignItems: "flex-end",
    borderRadius: 3,
    backgroundColor: "transparent",
    "& fieldset": {
      border: "none",
    },
  },
  "& textarea": {
    paddingTop: "12px",
    paddingBottom: "12px",
  },
}}
```

Use this send button style:

```tsx
sx={{
  width: 42,
  height: 42,
  flexShrink: 0,
  borderRadius: "50%",
  color: "#ffffff",
  backgroundColor: loading || !input.trim() ? "#9ca3af" : "#111827",
  "&:hover": {
    backgroundColor: loading || !input.trim() ? "#9ca3af" : "#1f2937",
  },
}}
```

Keep the helper caption under the composer with the text `Enter로 전송, Shift+Enter로 줄바꿈`.

- [ ] **Step 6: Restyle the right evidence panel**

Keep the same `result` data usage, but move it into a quieter support card:

```tsx
<PageCard
  title="분석 근거"
  subtitle="선택된 concept, agent, trace 요약"
>
```

Use muted section headings and keep all chips functional. When no result exists, show a simple placeholder with helper copy instead of a highly styled empty card.

- [ ] **Step 7: Run frontend build after the full chat workspace rewrite**

Run: `npm run build`

Expected: build completes successfully.

- [ ] **Step 8: Visually verify the local app in the browser**

Open: `http://127.0.0.1:13000/login`

Log in using the existing local admin API key from the workspace environment, then verify:

- sidebar uses the darker rail style
- topbar is slim and sticky
- chat empty state shows welcome text and prompt chips
- prompts disappear after the first message
- user and assistant messages use the new flatter styling
- evidence panel remains visible on wide screens

Expected: the chat page feels closer to ChatGPT while preserving the banking support panel.

- [ ] **Step 9: Commit the chat workspace rewrite**

```bash
git add frontend/src/components/chat/ChatWorkspace.tsx frontend/src/components/chat/MarkdownMessage.tsx
git commit -m "feat: refresh chat workspace layout"
```

## Self-Review

- Spec coverage: theme, shell, topbar, sidebar, flatter assistant responses, empty state, prompt behavior, composer, responsive three-column layout, and evidence panel retention are all mapped to tasks above.
- Placeholder scan: removed generic TODO language; each task contains concrete file targets, code, or commands.
- Type consistency: plan keeps existing `ChatSession`, `ChatResponse`, and message-role contracts intact; no API contract changes introduced.
