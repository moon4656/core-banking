# App Shell Navigation Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 메뉴 클릭 후 지연되는 체감을 줄이기 위해 보호된 화면에서 공통 셸을 유지하고 세션 검증을 최초 진입 시 한 번만 수행한다.

**Architecture:** App Router route group 아래에 보호 레이아웃을 두고 여기서 `AppShell`을 단 한 번 렌더링한다. 각 페이지는 셸을 직접 감싸지 않고 제목만 제공하며, 사이드바는 클릭 즉시 피드백을 보여준다.

**Tech Stack:** Next.js App Router, React client components, MUI, existing localStorage session helpers

---

### Task 1: Protected Layout 도입

**Files:**
- Create: `frontend/src/app/(protected)/layout.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`

- [ ] 보호 화면용 route group 레이아웃을 추가해 `AppShell`이 children을 감싸도록 만든다.
- [ ] `AppShell`이 외부에서 제목을 받지 않고 현재 pathname 기반 제목을 계산하도록 바꾼다.
- [ ] 세션 검증은 `AppShell` 최초 마운트 시 1회만 수행하도록 유지한다.

### Task 2: 페이지 중복 셸 제거

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`
- Modify: `frontend/src/app/ai/chat/page.tsx`
- Modify: `frontend/src/app/inquiry/concepts/page.tsx`
- Modify: `frontend/src/app/analysis/traces/page.tsx`
- Modify: `frontend/src/app/admin/concepts/page.tsx`
- Modify: `frontend/src/app/admin/aliases/page.tsx`
- Modify: `frontend/src/app/admin/relations/page.tsx`
- Modify: `frontend/src/app/admin/agent-mappings/page.tsx`
- Modify: `frontend/src/app/admin/concept-api-mappings/page.tsx`
- Modify: `frontend/src/app/admin/agents/page.tsx`
- Modify: `frontend/src/app/admin/apis/page.tsx`

- [ ] 각 페이지에서 `AppShell` 감싸기를 제거하고 본문만 반환하도록 정리한다.
- [ ] 보호 대상 페이지 파일들을 route group 경로로 이동하거나 레이아웃 적용 경로로 맞춘다.

### Task 3: 메뉴 클릭 즉시 피드백

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] 현재 경로와 별도로 pending 메뉴 상태를 둬서 클릭 즉시 선택 스타일이 반응하게 만든다.
- [ ] 이동 완료 후 pending 상태를 현재 pathname에 맞춰 정리한다.

### Task 4: 검증

**Files:**
- Modify: `frontend/src/components/chat/normalizeMarkdown.test.ts`

- [ ] 보호 레이아웃 경로 변경 후 타입 오류가 없는지 `tsc`로 확인한다.
- [ ] 프런트 컨테이너를 재시작하고 메뉴 클릭 후 페이지 응답을 수동 검증한다.
