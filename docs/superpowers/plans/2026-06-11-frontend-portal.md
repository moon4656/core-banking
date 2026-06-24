# Frontend Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a phase-1 Next.js portal that unifies login, chat, inquiry, analysis, and admin navigation on top of the existing FastAPI backend.

**Architecture:** Keep the current FastAPI backend and mock API unchanged for the first phase. Add a standalone `frontend` workspace that consumes the existing `/api/v1/ai`, `/api/v1/knowledge`, and `/api/v1/ai/traces/*` endpoints, with a shared application shell and role-aware client session.

**Tech Stack:** Next.js 15, React 18, TypeScript, MUI, MUI Data Grid, React Query, React Hook Form, Zod

---

### Task 1: Create the frontend workspace skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/next-env.d.ts`
- Create: `frontend/eslint.config.mjs`

- [ ] Define a minimal Next.js app workspace with the required dependencies and scripts.
- [ ] Add TypeScript and Next.js config files so the app can build once dependencies are installed.

### Task 2: Add shared app infrastructure

**Files:**
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/providers.tsx`
- Create: `frontend/src/lib/query-client.ts`
- Create: `frontend/src/lib/theme.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/session.ts`

- [ ] Add shared providers for MUI and React Query.
- [ ] Add a small client-side session helper that stores the selected role and API key.
- [ ] Add fetch helpers for GET and POST requests against the FastAPI backend.

### Task 3: Build the shared shell and navigation

**Files:**
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Topbar.tsx`
- Create: `frontend/src/components/common/PageCard.tsx`

- [ ] Add the application shell with sidebar, topbar, and content region.
- [ ] Keep the visual language simple and operational, with room for later admin screens.

### Task 4: Implement the first-phase screens

**Files:**
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/ai/chat/page.tsx`
- Create: `frontend/src/app/inquiry/concepts/page.tsx`
- Create: `frontend/src/app/analysis/traces/page.tsx`
- Create: `frontend/src/app/admin/concepts/page.tsx`

- [ ] Add a role-based login screen that stores a name, role, and API key locally.
- [ ] Add a dashboard with quick links and first-phase guidance.
- [ ] Add a chat screen wired to `POST /api/v1/ai/chat`.
- [ ] Add a concept inquiry screen wired to the knowledge endpoints.
- [ ] Add a trace analysis screen driven by `request_id` lookup using the existing trace endpoints.
- [ ] Add an admin placeholder page that explains which CRUD APIs are needed next.

### Task 5: Add reusable feature components and types

**Files:**
- Create: `frontend/src/components/chat/ChatWorkspace.tsx`
- Create: `frontend/src/components/grid/BaseDataGrid.tsx`
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/types/concept.ts`
- Create: `frontend/src/types/trace.ts`

- [ ] Define client-facing types that match the current backend response payloads.
- [ ] Add reusable chat and grid components so later CRUD screens can share the same patterns.

### Task 6: Add runtime and container glue

**Files:**
- Create: `frontend/.env.local.example`
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `README.md`

- [ ] Add a frontend container that runs on port `13000` and talks to the backend on `18000`.
- [ ] Document the new startup flow and environment values.

### Task 7: Verify the scaffold

**Files:**
- Verify: `frontend/**/*`
- Verify: `docker-compose.yml`
- Verify: `README.md`

- [ ] Run lightweight verification where possible in the current environment.
- [ ] Call out anything that still needs `npm install` or a full browser run outside the current sandbox.
