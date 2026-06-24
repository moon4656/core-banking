# ChatGPT-Style Chat UI Refresh

## Goal

Refresh the frontend so the chat experience feels closer to ChatGPT while preserving the trust and clarity expected in a banking operations portal.

## Scope

This change covers the authenticated frontend shell and the AI chat page:

- `frontend/src/components/chat/ChatWorkspace.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/Topbar.tsx`
- `frontend/src/components/common/PageCard.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/lib/theme.ts`

The login screen is out of scope unless a shared theme tweak incidentally improves it.

## Design Direction

### Overall layout

Use a three-column page structure:

- Left: a dark, compact navigation rail that feels closer to ChatGPT's sidebar
- Center: a wide conversation canvas with minimal card framing
- Right: a quieter supporting panel for trace, concept, and agent evidence

The center column should visually dominate. The right panel remains visible on large screens to preserve the banking workflow context.

### Banking tone retention

Keep the overall interface restrained and operational rather than consumer-social:

- Base palette: off-white, charcoal, slate, soft gray
- Accent palette: controlled banking blue for important actions and selected states
- Motion: subtle only, limited to hover and focus polish
- Typography: keep current system-safe Korean-friendly font stack unless a broader branding change is requested

### Top bar

Reduce the top bar from a large page-header treatment to a slim contextual header:

- Smaller vertical height
- Muted subtitle or optional status text
- Session metadata retained but visually de-emphasized

### Sidebar

Reshape the sidebar to feel more like a conversation workspace navigator:

- Dark matte background
- Simpler menu rows
- Lower contrast borders
- A clearer selected state
- Session/account block visually integrated near the bottom

Do not remove existing admin navigation items.

## Chat Page Behavior

### Conversation area

The chat page should behave like a focused assistant workspace:

- Remove the heavy card-within-card feel
- Increase the usable message width in the main column
- Keep assistant messages visually light and easy to scan
- Keep user messages compact and clearly separated

Assistant messages should look native to the page rather than like large document cards. Markdown rendering remains intact.

### Empty state

When no messages exist:

- Show a wider, calmer welcome state
- Present a concise heading and helper copy
- Show suggested prompts as pill actions

Suggested prompts should only appear before a conversation starts.

### Input composer

Adopt a ChatGPT-like bottom composer:

- Wide rounded container
- Multiline input
- Send button anchored within the composer
- Minimal chrome around the input

Keep Enter-to-send and Shift+Enter-for-newline behavior.

### Right-side evidence panel

Retain operational value but lower visual weight:

- Present request ID, concepts, agents, and evidence counts in a tidy support panel
- Match the new shell visually
- Avoid competing with the central conversation

## Responsive Behavior

### Desktop

- Three columns on wide screens
- Center column receives priority width
- Right panel stays visible when space allows

### Tablet

- Sidebar remains available
- Right panel moves below the conversation if needed

### Mobile

- Single-column stacking
- Composer remains comfortable to use
- No fixed sizing that causes clipping

## Implementation Approach

### Option considered

Three approaches were considered:

1. Conservative restyle of existing cards
2. Balanced restructuring with ChatGPT-inspired center layout and retained banking support panel
3. Near-full ChatGPT clone with most operational elements hidden or moved away

The selected approach is option 2 because it improves familiarity without sacrificing banking workflow context.

## Testing Plan

- Run frontend build or lint if available in this project setup
- Open the local app and visually verify:
  - login screen still works
  - sidebar navigation remains usable
  - chat empty state renders correctly
  - message list spacing and alignment look correct
  - composer remains usable on long input
  - right-side evidence panel still updates after a response

## Risks And Mitigations

### Risk: layout regression on smaller screens

Mitigation: use responsive grid breakpoints and avoid hard-coded panel widths where possible.

### Risk: banking support metadata becomes too hidden

Mitigation: keep the right panel visible on large screens and stacked below on smaller screens.

### Risk: assistant markdown styling becomes less readable after simplification

Mitigation: keep markdown component behavior unchanged and only adjust container presentation.

## Success Criteria

- The chat page feels noticeably closer to ChatGPT in structure
- The portal still feels appropriate for a banking operations tool
- Existing chat functionality continues to work
- Analysis metadata remains accessible
