# Part 2 PR-3 Part A — Refine Primitive Migration Survey

**Date:** 2026-07-28  
**Branch:** `feat/universal-chat-tools` @ `bcf3a5d`  
**Mode:** Read-only. `npx tsc --noEmit` baseline only (exit 0).  
**Prior:** `design-consistency-survey.md`, `p2-pr1-insight-signal-panelheader-survey.md`, `p2-pr2-evidence-report-side-survey.md`, `loading-flash-survey.md`, `p2-pr4-launch-dedup-survey.md`, `p2-pr2b-report-canvas-survey.md`. Not re-audited here.

---

## Load-bearing finding (read first)

**Live product Refine is not the `ra-*` / `rt-*` stack.**

| Stack | Location | Mounted in product? | Styling |
|-------|----------|---------------------|---------|
| **A — Canvas Refine (live)** | `frontend/components/experiment/refine/` + `nodes/RefineExpandedNode` / `RefineFullscreenModal` | Yes — `ExperimentCanvas` | Mostly brutalist tokens (`border-border-master`, `shadow-brutal-*`, `font-mono text-mono-*`); leftover `fv-*` CSS vars in message bubbles |
| **B — Ascent / peak narrative** | `frontend/components/refinement/` + `chat/ChatInterface` | **No** live dashboard mount; demos only (`/refinement-demos`, `QuestMapExperience`) | Heavy `ra-*` / `rt-*` + `fv-*` |

`RefineStagePanel` wraps `ChatInterface` but has **zero importers** outside its own file. DeepDive has no Refine tab — Evidence / Launch / Signal only.

PR-3’s “preserve narrative” boundary applies to Stack B (and its CSS). Stack A is what founders use after Spark; it never imports `refinement-ascent.css` / `refinement-thread.css`.

---

## 1. Refine surface inventory

### 1a. `frontend/components/refinement/` (Stack B — narrative)

| File | LOC | Export | Purpose | Style |
|------|-----|--------|---------|-------|
| `ClarifyingQuestionBlock.tsx` | 447 | `ClarifyingQuestionBlock` | Multi-step clarifying Q wizard (+ past-turn edit) | **mixed** (`ra-*`/`rt-*` + `fv-btn-*` + `bg-black/50` modal) |
| `RefinementThreadMessage.tsx` | 435 | `RefinementThreadMessage` | Ascent/peak chapter message renderer | **narrative** (`ra-*`/`rt-*`) + `fv-btn-*` edit actions |
| `refinement-ascent.css` | 386 | — | Ascent visual language (`.ra-*`) | **narrative** |
| `__tests__/ClarifyingQuestionBlock.test.tsx` | 334 | — | Unit + snapshot tests | — |
| `refinement-thread.css` | 252 | — | Thread step/card/clarity chips (`.rt-*`) | **narrative** |
| `PressureTestSection.tsx` | 142 | `PressureTestSection` | “Chapter 2” Q&A carousel card | **narrative** + `fv-btn-*` |
| `ClarityAnswerCarousel.tsx` | 73 | `ClarityAnswerCarousel` | Q&A carousel inside pressure/ascent | **narrative** |
| `ClarifyingQuestionsLoading.tsx` | 66 | `ClarifyingQuestionsLoading` | Loading skeleton for clarify batch | **narrative** (`ra-*`) |
| `RefineStagePanel.tsx` | 23 | `RefineStagePanel` | Thin wrapper → `ChatInterface` | **fv-***; **unmounted** |

### 1b. `frontend/components/experiment/refine/` (Stack A — live)

| File | LOC | Export | Purpose | Style |
|------|-----|--------|---------|-------|
| `useRefineChat.ts` | 406 | `useRefineChat`, `MCQItem`, `McqSendMeta` | Chat load/send/edit/retry/branch/MCQ state | logic only |
| `RefineChatMessage.tsx` | 421 | `RefineChatMessage`, `RefineChatMessageModel` | Single message + assistant MCQ affordances | **mixed** (brutalist chrome + `fv-*` vars) |
| `LiveWorkspacePanel.tsx` | 343 | `LiveWorkspacePanel` | Fullscreen right rail: idea card, log, finalize/reset | **brutalist** |
| `RefineMCQPopup.tsx` | 290 | `RefineMCQPopup`, `computeCenteredMcqPosition` | Draggable portal MCQ | **brutalist** (+ `fv-brutal-hover`) |
| `RefineChatInput.tsx` | 240 | `RefineChatInput`, `AttachmentDraft` | Composer + attachments | **brutalist** (`text-red-600` error) |
| `RefinedIdeaCard.tsx` | 183 | `RefinedIdeaCard` | Refined idea display / flash | **brutalist** |
| `RefineChatScroll.tsx` | 126 | `RefineChatScroll` | Message list + load/empty/opener states | **brutalist** |
| `MessageActions.tsx` | 95 | `MessageActions` | Edit / retry / branch chrome | **brutalist** |
| `LogEntryCard.tsx` | 72 | `LogEntryCard` | Workspace log entry | **brutalist** |
| `BranchNavigator.tsx` | 58 | `BranchNavigator` | Sibling prev/next | **brutalist** |
| `BrutalistConfirm.tsx` | 57 | `BrutalistConfirm` | Confirm dialog (finalize/reset) | **brutalist** |
| `MessageAttachments.tsx` | 52 | `MessageAttachments` | Attachment chips on messages | **brutalist** |
| `formatLocalTime.ts` | 9 | helper | Timestamp formatting | — |

**Frame mounts:**

| File | LOC | Export | Purpose | Style |
|------|-----|--------|---------|-------|
| `nodes/RefineExpandedNode.tsx` | 123 | `RefineExpandedNode` | Windowed React Flow node (560px panel) | **brutalist** custom header |
| `nodes/RefineFullscreenModal.tsx` | 152 | `RefineFullscreenModal` | Portal fullscreen shell + workspace split | **brutalist** custom header |

Collapsed canvas node is shared `ActNode` (`id: "refine"`), not a Refine-specific component.

### 1c. `frontend/components/chat/` (Refine-adjacent)

| File | LOC | Export | Role |
|------|-----|--------|------|
| `ChatInterface.tsx` | 1062 | `ChatInterface` | Full refine+research chat; mounts Stack B narrative components; **not** used by canvas Refine |
| `ChatInput.tsx` | 279 | `ChatInput` | fv-* composer for `ChatInterface` only |
| `ChatMessage.tsx` | 138 | `ChatMessage` | fv-* bubble; **not** used by canvas Refine (canvas uses `RefineChatMessage`) |
| `ChatMarkdown.tsx` | 58 | `ChatMarkdown` | Shared markdown; used by Stack B, UniversalChatDock, not by `RefineChatMessage` |

### 1d. Live mount points

```709:728:frontend/components/experiment/ExperimentCanvas.tsx
  const onNodeClick: NodeMouseHandler = (_, node) => {
    // ...
    if (node.id === "refine") {
      openRefinePanel();
      return;
    }
```

```390:416:frontend/components/experiment/ExperimentCanvas.tsx
  const openRefinePanel = useCallback(() => {
    const lockState = getNodeLockState("refine", experiment);
    // ... lock toast / reopen confirm ...
    setRefinePanelOpen(true);
    // closes Spark; setRefineUrl(true)
  }, [/* ... */]);
```

- **Windowed:** `refinePanelOpen && !refineFullscreen` → React Flow node `refine-expanded` → `RefineExpandedNode`.
- **Fullscreen:** `refineFullscreen` → portal `RefineFullscreenModal` (Escape minimizes unless MCQ active).
- **MCQ:** `activeMCQ && refineSurfaceOpen` → `RefineMCQPopup` sibling under canvas (not inside message list).
- **DeepDive:** no Refine act — `overlayAct` is evidence | launch | signal only.
- **UniversalChatDock:** separate right-dock; co-mounted on canvas; does **not** import refine hooks/components.

---

## 2. `ra-*` / `rt-*` — narrative layer (do not touch for primitive migration)

### File counts / locations

**`.ra-*` consumers / definitions (8 TSX/CSS files under frontend product paths):**

- `refinement/refinement-ascent.css` — **~55** top-level `.ra-*` rules
- `refinement/ClarifyingQuestionBlock.tsx`, `ClarifyingQuestionsLoading.tsx`, `ClarityAnswerCarousel.tsx`, `PressureTestSection.tsx`, `RefinementThreadMessage.tsx`
- `chat/ChatInterface.tsx` — wraps story in `<article className="ra-story">` (~L1001)
- `refinement-demos/RefinementAscentDemo.tsx`

**`.rt-*`:**

- `refinement/refinement-thread.css` — **~36** top-level `.rt-*` rules
- Used from `ClarifyingQuestionBlock.tsx`, `RefinementThreadMessage.tsx`
- Unrelated false-positive hits in `lib/validation-report-*.ts` (not Refine)

**Zero** `ra-` / `rt-` matches under `experiment/refine/` or Refine nodes.

### Visual pattern

CSS-driven **editorial chapter layout**, not SVG/canvas:

- **Ascent (`.ra-*`):** hero quote for spark idea, section heads, Q&A carousel (`.ra-qa-*`), finale before/after upgrade (`.ra-finale*`), kicker labels — “refinement as story chapters.”
- **Thread (`.rt-*`):** vertical step rail (`.rt-step` / `.rt-step-marker`), spark vs refined cards, clarity chips, upgrade grid, clarify progress panel.

Icons are lucide/`svg` inside CSS-sized markers; animations are CSS/`animate-spin` (loading). No canvas or Framer Motion in the narrative package.

### Narrative vs generic-inside-folder

| Narrative (preserve) | Generic / reinvented chrome inside same files |
|----------------------|-----------------------------------------------|
| `refinement-ascent.css`, `refinement-thread.css` | `fv-btn-primary` / `fv-btn-ghost` EditActions in `RefinementThreadMessage`, `PressureTestSection` |
| `RefinementThreadMessage` chapter structure | `ClarifyingQuestionBlock`’s `ConfirmRegenerateModal` (`bg-black/50`) |
| `PressureTestSection`, `ClarityAnswerCarousel` | Wizard option buttons / submit row styling (mixed with `ra-*` panels) |
| `ClarifyingQuestionsLoading` ascent skeleton | `RefineStagePanel` fv border wrapper |
| Peak/ascent `variant` props | — |

---

## 3. Shared primitives reinvented in Refine (migrate candidates)

Focus on **Stack A (live)** unless noted. Stack B listed where a brutalist equivalent would apply if that path is revived.

| Primitive | Where reinvented | Brutalist equivalent exists? |
|-----------|------------------|------------------------------|
| **Panel / phase header** | `RefineExpandedNode` L66–80 (`bg-ink-primary` grab bar “PHASE 02: REFINE // EXPANDED_VIEW”); same pattern in `RefineFullscreenModal` L81–98 | **`PanelHeader`** (`components/ui/PanelHeader.tsx`) — Signal/Evidence pattern; current Refine headers are darker ink bars, not `PanelHeader` |
| **Chat composer** | `RefineChatInput` — own border-2 / send / paperclip | No shared brutalist composer; Universal dock reinvents again (fv vars). Evidence chat N/A. Separate from `ChatInput` (fv) |
| **Send / primary / secondary buttons** | Inline classes across input, MCQ submit, finalize, `BrutalistConfirm` | No single Button primitive; patterns duplicated. `BrutalistConfirm` is Refine-local (not `TypeConfirmDialog`) |
| **Empty state** | `RefineChatScroll` empty + opener copy (mono uppercase) | **`EmptyState`** exists; not used |
| **Loading** | `RefineChatScroll` text “Loading conversation…”; opener pulse bolt; message regenerating dots | **`BrutalistSkeleton`**, **`LoadingState`** exist; not used |
| **Error** | Hook `error` string; input `text-red-600`; failed message `error: true` opacity | **`ErrorBanner`** exists; not used. Hardcoded red hazard |
| **MCQ popup** | `RefineMCQPopup` (portal, drag, multi-select + custom) | Stack B uses inline `ClarifyingQuestionBlock` (different UX). No shared MCQ primitive |
| **Message bubbles / rows** | `RefineChatMessage` (user vs REFINER) | Distinct from `ChatMessage` / Universal dock bubbles / Stack B `RefinementThreadMessage` — **three** message UIs |
| **Attachments** | `RefineChatInput` drafts + `MessageAttachments` | Not shared with Universal dock (paperclip disabled there) |
| **Confirm dialogs** | `BrutalistConfirm` | Nearby: `TypeConfirmDialog` (type-to-confirm). Different API |

**Already largely brutalist on live path:** composer chrome, MCQ surface, workspace panel, branch navigator, idea card — migration is **token cleanup + header/loading/error convergence**, not a greenfield rewrite.

**Stack B reinvented chrome (if in scope):** entire `ChatInput` / `ChatMessage` / `ChatInterface` shell (`fv-*`), plus `fv-btn-*` inside narrative components — keep `ra-*`/`rt-*` markup, swap chrome only.

---

## 4. Refine chat implementation details (Stack A)

### `useRefineChat.ts`

State: `messages`, `loading`, `generatingOpener`, `sending`, `threadId`, `error`, `reloadToken`, `activeMCQ`, `dismissedMCQMessageIds`, `refinementCount`, `navigatingMessageId`, `regeneratingMessageId`.

Message model maps history with `parent_message_id`, `sibling_index`, `sibling_count` (L33–46). Branch switch calls `setActiveBranch` / `getMessageSiblings`. MCQ picked from assistant `clarifying_questions` via `pickActiveMCQ`. Send supports `McqSendMeta`. Edit/retry/regenerate paths reload history.

### Message rendering

- Single message: **`RefineChatMessage`** via **`RefineChatScroll`**.
- Not shared with Evidence; not `ChatMessage`; not `RefinementThreadMessage`.

### Windowed vs fullscreen

- Toggle: `openRefineFullscreen` / `minimizeRefineFullscreen` on canvas; expanded node `onFullscreen`; fullscreen Escape → minimize (blocked while `mcqActive`).
- Fullscreen adds **`LiveWorkspacePanel`** (idea finalize rail); windowed is chat-only column.

### MCQ

- Component: **`RefineMCQPopup`**.
- Trigger: after turn, `response.clarifying_questions` → `setActiveMCQ`; restored on reload from latest assistant message; reopen via message UI → `reopenMCQ`.
- Render: portal from **`ExperimentCanvas`** when `activeMCQ && refineSurfaceOpen`.

---

## 5. Window frame + entry points

- **Mount:** canvas overlay surfaces — React Flow expanded node **or** fullscreen portal — **not** a route, not DeepDive.
- **Same component tree:** both modes share `RefineChatScroll` / `RefineChatInput` / `useRefineChat`; fullscreen only adds workspace.
- **URL:** `?act=refine` syncs panel open (popstate handler ~L433–444).
- DeepDive Refine tab: **does not exist.**

---

## 6. Hardcoded color hazards

### Stack A (live) — migrate-relevant

| Hit | File | Notes |
|-----|------|-------|
| `text-red-600` | `RefineChatInput.tsx` ~L202 | Upload error — shared-primitive hazard |
| `var(--fv-code-*)`, `var(--fv-accent-muted)`, `var(--fv-surface-2)` | `RefineChatMessage.tsx` | Leftover fv tokens inside brutalist bubbles |
| `fv-brutal-hover` / `fv-brutal-hover-glow` | `RefinedIdeaCard`, `RefineMCQPopup` | Utility class name; visual already brutalist |

No `#000` / `#fff` / `text-white` / `bg-black` / Tailwind palette greys in Stack A nodes/input (aside from `text-red-600`).

### Stack B (narrative) — intentional stay vs chrome

| Hit | Classification |
|-----|----------------|
| `refinement-ascent.css` `#0f172a`, `#111827`, `#f8fafc` in dark `.ra-finale` | **Narrative** — stay with ascent CSS |
| `ClarifyingQuestionBlock` `bg-black/50` modal | **Chrome** — migrate if Stack B touched |
| `ChatInput` `rgba(0,0,0,0.25)`, `text-red-400` | **Chrome** (fv stack) |

---

## 7. Refine-specific behaviors to preserve

| Behavior | Where |
|----------|--------|
| Message tree / siblings (`parent_message_id`, sibling nav) | `useRefineChat` + `BranchNavigator` |
| Chat history load + opener generation | `useRefineChat` load effect |
| Refined idea preview / finalize / reset | `LiveWorkspacePanel`, `RefinedIdeaCard`, `finalizeRefinement` / `resetRefineSession` |
| WIP idea updates | Server-driven `experiment.refined_idea_current`; panel **flash** on change — **no** frontend debounce editor autosave in this tree |
| Attachment upload | `RefineChatInput` + `uploadChatAttachments` in send path |
| MCQ answer flow | `RefineMCQPopup` → `answerMCQ` → `send` with meta |
| Windowed / fullscreen | Canvas state + URL `act=refine` |
| Reopen confirm after certain statuses | `openRefinePanel` + `window.confirm` |

These need variant props or stay Refine-owned; a generic `PanelHeader` / skeleton cannot absorb branching/MCQ/workspace alone.

---

## 8. Related shared surfaces

- **UniversalChatDock:** separate API (`getUniversalChatMessages` / `sendUniversalChatMessage`), own composer/bubbles; shares only **`ChatMarkdown`**. PR-3 on canvas Refine does **not** automatically restyle the dock; dock still mixed fv + brutalist border.
- **`ClarifyingQuestionBlock`:** real; tested; wired through **`ChatInterface`** only (Stack B), not canvas MCQ popup.
- **Canvas Refine node:** collapsed = shared **`ActNode`** (already brutalist). Expanded = `RefineExpandedNode`. Node chrome migration ≠ narrative.

---

## 9. Test surface

| Test | Notes |
|------|-------|
| `refinement/__tests__/ClarifyingQuestionBlock.test.tsx` | Only Refine-related unit tests found |
| `__snapshots__/ClarifyingQuestionBlock.test.tsx.snap` | **Will churn** if Stack B chrome/classes change |
| No `experiment/refine/**/*.test.*` | Live path untested at unit level |
| No `useRefineChat*` tests | — |
| `chat/**/*.test.*` | None found |

---

## 10. Size sanity check

**In-scope for “shared primitives on live Refine” (Stack A polish):**

Rough touch surface if headers → `PanelHeader`, loading/empty/error → ui primitives, strip `fv-*` from messages, light input/MCQ token alignment:

| Bucket | ~LOC |
|--------|------|
| Headers (expanded + fullscreen) | ~275 |
| `RefineChatScroll` empty/load | ~126 |
| `RefineChatMessage` token cleanup | ~421 |
| `RefineChatInput` error/token | ~240 |
| MCQ minor class cleanup | ~50–100 |

**Comfortable single PR ~800–1200 LOC touched** (many lines already correct; net diff smaller). Under 1000–2000 “big but doable.”

**If Stack B ChatInterface shell + clarify chrome also migrate (keeping `ra-*`/`rt-*` CSS/components):** add ~1062 + 279 + 138 + partial ClarifyingQuestionBlock → **2000+ → flag for split** (PR-3a live canvas; PR-3b orphan ChatInterface/demos).

Narrative CSS (~638 LOC) should **not** count toward migration LOC.

---

## 11. Baseline

```
bcf3a5d Part2 PR-2b: migrate ReportCanvas / ReportScoreSection / ExportMenu to brutalist
857277a Part2 PR-4: delete landing-page-editor/, dedup Launch on brutalist launch/ tree
a076af9 Loading flash fix: unify auth, add loading.tsx per route, three-state auth machine
```

`cd frontend && npx tsc --noEmit` → **exit 0** (2026-07-28).

---

## Findings summary (no proposals)

1. Product Refine = **canvas Stack A**; ascent/`ra-*`/`rt-*` = **Stack B**, demo/orphan.
2. Section 2 boundary = Stack B CSS + chapter components; Section 3 migrate list = Stack A headers/load/empty/error/fv leftovers (+ optional Stack B chrome if revived).
3. Three chat UIs coexist: Refine canvas, Universal dock, ChatInterface.
4. DeepDive has no Refine tab; entry is `ActNode` click → `openRefinePanel`.
