# Leader Evaluation Admin UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관리자 화면에서 리더 Agent 평가 목록과 상세 패널을 조회할 수 있는 UI를 추가한다.

**Architecture:** 기존 `Trace 분석` 페이지 패턴을 재사용해 새 관리자 페이지를 만든다. 공용 API 헬퍼와 `BaseDataGrid`, `PageCard`, `AppShell`을 활용해 목록과 상세를 같은 화면에서 보여준다.

**Tech Stack:** Next.js App Router, TypeScript, MUI, TanStack Query

---

### Task 1: Define frontend data contracts

**Files:**
- Create: `frontend/src/types/leaderEvaluation.ts`

- [ ] Define list/detail response types that match the new backend admin API.

### Task 2: Add navigation entry points

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] Add a new admin navigation item for `/admin/leader-evaluations`.
- [ ] Add a dashboard shortcut if the page currently exposes admin shortcuts there.

### Task 3: Build the admin page

**Files:**
- Create: `frontend/src/app/admin/leader-evaluations/page.tsx`

- [ ] Reuse the trace analysis layout pattern with a list grid, summary card, decision card, trace events grid, and evidence grid.
- [ ] Fetch list and detail data through `apiGet` and `useQuery`.
- [ ] Render safe fallback text for nullable review fields.

### Task 4: Verify integration

**Files:**
- No code changes required

- [ ] Run TypeScript validation for the frontend.
- [ ] Run a frontend Docker build so the new route is included in the production bundle.
