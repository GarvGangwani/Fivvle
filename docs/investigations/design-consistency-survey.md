# Design Consistency Survey — Part A

**Date:** 2026-07-27
**Branch:** `feat/universal-chat-tools` (4 commits ahead, unpushed)
**Scope:** Read-only audit of five act surfaces + shared primitives

---

## Executive Summary

The frontend has **two co-existing design systems** with zero shared styling DNA:

| System | Origin | Border | Shadow | Radius | Typography | Accent |
|--------|--------|--------|--------|--------|------------|--------|
| **Legacy fv-\*** | Early acts (Refine, Insight, older editor) | `border` 1px + `var(--fv-border)` | `shadow-xl`/`shadow-lg` or none | `rounded-xl`/`rounded-2xl` | `text-lg font-semibold`, raw px sizes | `var(--fv-accent)` purple + `color-mix()` |
| **Brutalist** | Later acts (Signal, Evidence editor/chat, Launch overlay) | `border-2 border-border-master` | `shadow-brutal-sm/md/lg` | `rounded-none` (implicit) | `font-headline`, `font-label-md`, `font-mono` uppercase | `bg-brutalist-yellow` |

Both systems define dark-mode tokens but use them differently. Neither uses Tailwind `dark:` variants — legacy uses `var(--fv-*)` CSS properties; brutalist uses semantic Tailwind tokens (`ink-primary`, `surface-card`, etc.) that resolve to the same CSS vars.

---

## Per-Act Findings

### Act 1 — Refine (Chat)

**System: Legacy fv-\* exclusively**

| Pattern | Implementation |
|---------|---------------|
| Panel header | None — chat starts immediately |
| Borders | `border border-[var(--fv-border)]` (1px) |
| Shadows | Hardcoded `rgba(0,0,0,0.25)` on ChatInput, not themed |
| Radius | `rounded-xl` / `rounded-2xl` / `rounded-full` |
| Typography | Raw px sizes (`text-[13px]`, `text-[15px]`), no semantic font classes |
| Buttons | `fv-btn-primary` / `fv-btn-ghost` |
| Loading | Pulsing dots (chat), centered text "Loading conversation..." |
| Error | Inline as chat messages, `text-red-400` (hardcoded!) in ChatInput |
| Dark mode | Via `var(--fv-*)` + CSS `[data-theme="dark"]` selectors |
| Scroll | Single `overflow-y-auto` on message container |

**Issues:**
- `text-red-400` hardcoded instead of `var(--fv-danger)`
- `rgba(0,0,0,0.25)` / `rgba(255,255,255,...)` hardcoded in ChatInput and globals.css utility classes
- No panel header — inconsistent with other acts
- Typography uses raw pixel sizes, not the semantic font scale

### Act 2 — Evidence (Research + Report)

**System: Split — brutalist (editor/chat/banner) + legacy (report viewers)**

| Component family | System |
|-----------------|--------|
| `EvidenceStagePanel`, `EvidenceReportEditor`, `EvidenceEditorToolbar`, `EditedDocOutdatedBanner`, `EvidenceChatPane`, `EvidenceSourcesBook` | Brutalist |
| `ReportCanvas`, `ValidationReportPanel`, `ValidationReportViewer`, `InlineResearchProgress`, `LandingGenerationProgress`, `TemplatePicker` | Legacy fv-\* |

**Issues:**
- Two design languages within one act
- `ValidationReportPanel` has hardcoded `rgba(255,255,255,0.07)` inline styles (dark-only)
- `LandingGenerationProgress` has hardcoded `rgba(255,255,255,0.04)` divider
- Loading: skeleton (`fv-skeleton`) in brutalist vs `Loader2 spinner` in legacy
- Error: `font-mono uppercase text-status-critical` in brutalist vs `fv-error` class in legacy

### Act 3 — Launch (Landing Page Editor)

**System: Two complete parallel implementations**

| Feature | System A (`landing-page-editor/`) | System B (`launch/`) |
|---------|----------------------------------|---------------------|
| Copy editor | `CopyFieldsEditor` | `LaunchCopyTab` |
| Color picker | `ColorThemePicker` (round swatches) | `ColorThemePanel` (square swatches) |
| Icon picker | `BrandIconPicker` (rounded buttons) | `BrandIconPanel` (square buttons) |
| Surface picker | `SurfaceStylePicker` (pill options) | `SurfaceAtmospherePanel` (chip options) |
| Slider | `DesignSlider` (CSS-painted) | `BrutalistSlider` (native + brutal badge) |
| Collapsible | `CollapsibleSection` (chevron, 1px, rounded) | `DesignCollapsibleCard` (material icon, 2px, square) |
| Template picker | `TemplatePicker` (live thumbs, rounded) | `TemplatePanel` (wireframe mocks, square) |
| Preview | `DevicePreview` + iframe | `LivePagePreviewPanel` + iframe |

**Issues:**
- Near-complete duplication of every editor feature across two design systems
- This is the worst drift — not just styling differences but **duplicate components**

### Act 4 — Signal (Metrics + Verdict)

**System: Brutalist exclusively — internally consistent**

| Pattern | Implementation |
|---------|---------------|
| Panel header | Sticky `border-b-2 border-border-master bg-surface-elevated` with `font-mono` phase label + `font-headline` title |
| Borders | `border-2 border-border-master` everywhere |
| Shadows | `shadow-brutal-sm` (secondary), `shadow-brutal-md` (primary) |
| Radius | None — all square |
| Typography | `font-headline`, `font-label-md`, `font-mono` — full semantic scale |
| Buttons | `border-2 border-border-master bg-brutalist-yellow shadow-brutal-md hover:-translate-y-0.5` |
| Loading | Skeleton: `border-2 border-border-master bg-surface-elevated animate-pulse` |
| Error | `font-mono text-mono-sm uppercase text-status-critical` in brutal card |
| Scroll | `SignalStagePanel` owns scroll, `max-w-2xl` centered |

**Issues:**
- `SignalInsightReport` and `SignalFounderDecisionPanel` are **duplicates** of Insight's `InsightReportViewer` and `DecisionPanel` — same data, different design system

### Act 5 — Insight (Report + Decision)

**System: Legacy fv-\* exclusively**

| Pattern | Implementation |
|---------|---------------|
| Panel header | None — no phase label, no title bar |
| Borders | `border border-[var(--fv-border)]` / `fv-section-card` / `fv-card` |
| Shadows | Via utility classes only |
| Radius | `rounded-xl` / `rounded-2xl` |
| Typography | Standard Tailwind `text-lg font-semibold`, sentence case — no `font-headline`/`font-label-md` |
| Buttons | `fv-btn-primary` / `fv-btn-ghost rounded-xl` |
| Loading | `<LoadingState>` shared component (spinner) |
| Error | `<ErrorBanner>` shared component |
| Scroll | `overflow-y-auto` on outer flex-col |

**Issues:**
- No panel header — inconsistent with Signal/Evidence brutalist acts
- `InsightReportViewer` and `DecisionPanel` are the legacy duplicates of Signal's brutalist versions
- Source badges use hardcoded Tailwind colors (`purple-500/15`, `indigo-500/15`)

---

## Shared Primitives Audit

### Token System (globals.css + tailwind.config.ts)

Both systems resolve to the same `--fv-*` CSS custom properties, but consume them differently:

| Concern | Legacy access | Brutalist access |
|---------|--------------|-----------------|
| Text color | `text-[var(--fv-text)]` | `text-ink-primary` |
| Border color | `border-[var(--fv-border)]` | `border-border-master` |
| Surface | `bg-[var(--fv-surface)]` | `bg-surface-card` |
| Accent | `var(--fv-accent)` | `bg-brand-primary` |

The Tailwind config maps both naming conventions to the same CSS vars, so dark mode works for both. But the **semantic gap** creates maintenance burden — every new developer must learn two vocabularies.

### Shared UI Components

| Component | System | Used by |
|-----------|--------|---------|
| `LoadingState` | Legacy | Insight, Evidence (report) |
| `ErrorBanner` | Legacy | Insight, Evidence (report), Dashboard |
| `EmptyState` | Legacy | Dashboard |
| `BrutalistSkeleton` | Brutalist | Dashboard (?) |
| `TypeConfirmDialog` | Legacy | Experiment shell |
| `ToastProvider` | Legacy | Everywhere |
| `PageHeader` | Legacy | Dashboard |

No shared brutalist primitives exist — each brutalist act re-implements cards, headers, badges, errors inline.

### Hardcoded Values (dark-mode hazards)

| File | Value | Should be |
|------|-------|-----------|
| `ChatInput.tsx` | `shadow-[0_-4px_24px_rgba(0,0,0,0.25)]` | `var(--fv-shadow-color)` based |
| `ChatInput.tsx` | `text-red-400` | `text-[var(--fv-danger)]` |
| `globals.css` `.fv-icon-btn` | `rgba(255,255,255,0.08)` | Should have light override |
| `globals.css` `.fv-input` | `rgba(255,255,255,0.08)` | Should have light override |
| `ValidationReportPanel.tsx` | `rgba(255,255,255,0.07)` inline | `var(--fv-border)` |
| `LandingGenerationProgress.tsx` | `rgba(255,255,255,0.04)` inline | `var(--fv-border)` |
| `InsightReportViewer.tsx` | `purple-500/15`, `indigo-500/15` | Semantic token |

---

## Drift Matrix

| Dimension | Refine | Evidence (editor) | Evidence (report) | Launch (editor) | Launch (overlay) | Signal | Insight |
|-----------|--------|-------------------|-------------------|-----------------|------------------|--------|---------|
| Border width | 1px | 2px | 1px | 1px | 2px | 2px | 1px |
| Border color | fv-border | border-master | fv-border | fv-border | border-master | border-master | fv-border |
| Shadow | hardcoded | brutal-sm | shadow-lg/none | shadow-2xl | brutal-sm/md | brutal-sm/md | via class |
| Radius | xl/2xl | none | xl/lg | xl/lg | none | none | xl/2xl |
| Panel header | none | brutal sticky | legacy sticky | CSS module | brutal sticky | brutal sticky | none |
| Typography | raw px | font-mono upper | raw px | raw px | font-headline | font-headline | text-lg semibold |
| Primary btn | fv-btn-primary | brutal retry | fv-btn-primary | fv-btn-primary | brutal yellow | brutal yellow | fv-btn-primary |
| Loading | pulsing dots | fv-skeleton | Loader2 spin | fv-skeleton | brutal skeleton | brutal skeleton | LoadingState |
| Error | chat inline | brutal mono | fv-error/ErrorBanner | toast | brutal mono | brutal mono | ErrorBanner |
| Empty | starter chips | n/a | n/a | n/a | mono uppercase | mono uppercase | text-muted |

---

## Duplicate Components

| Functionality | Legacy version | Brutalist version |
|--------------|----------------|-------------------|
| Insight report viewer | `insight/InsightReportViewer.tsx` | `signal/SignalInsightReport.tsx` |
| Founder decision panel | `insight/DecisionPanel.tsx` | `signal/SignalFounderDecisionPanel.tsx` |
| Copy editor | `landing-page-editor/CopyFieldsEditor.tsx` | `launch/LaunchCopyTab.tsx` |
| Color picker | `landing-page-editor/ColorThemePicker.tsx` | `launch/ColorThemePanel.tsx` |
| Icon picker | `landing-page-editor/BrandIconPicker.tsx` | `launch/BrandIconPanel.tsx` |
| Surface picker | `landing-page-editor/SurfaceStylePicker.tsx` | `launch/SurfaceAtmospherePanel.tsx` |
| Slider | `landing-page-editor/DesignSlider.tsx` | `launch/BrutalistSlider.tsx` |
| Collapsible section | `landing-page-editor/CollapsibleSection.tsx` | `launch/DesignCollapsibleCard.tsx` |
| Template picker | `research/TemplatePicker.tsx` | `launch/TemplatePanel.tsx` |

---

## Recommended Unification PRs

**Decision prerequisite:** Which system wins? The brutalist system is more internally consistent and has the newer components, but the legacy system backs the Refine chat (the highest-touch surface). This is a design decision for Chaitanya before code work begins.

Assuming brutalist wins (pending confirmation):

| PR | Scope | Estimated size |
|----|-------|---------------|
| PR-5 | **Shared brutalist primitives** — extract `BrutalistCard`, `BrutalistHeader`, `BrutalistBadge`, `BrutalistError`, `BrutalistEmpty` from Signal into `components/ui/` | S |
| PR-6 | **Insight → brutalist** — rewrite `InsightReportViewer` and `DecisionPanel` using shared primitives, then delete Signal's duplicates | M |
| PR-7 | **Launch dedup** — delete `landing-page-editor/` System A components, wire standalone editor route to `launch/` System B components | L |
| PR-8 | **Evidence report viewers → brutalist** — migrate `ReportCanvas`, `ValidationReportPanel`, `ValidationReportViewer` | M |
| PR-9 | **Refine chat → brutalist** — migrate `ChatInterface`, `ChatInput`, `RefinementThreadMessage` (largest, most delicate — touches the ascent/peak variants) | L |
| PR-10 | **Hardcoded values cleanup** — replace all `rgba(...)` hardcodes with token references, fix `text-red-400` | S |
| PR-11 | **Dark mode compliance** — audit all `var(--fv-*)` globals.css utility classes for light/dark correctness | S |
| PR-12 | **Typography normalization** — eliminate raw `text-[Npx]` in favor of the semantic font scale everywhere | M |

---

## Open Questions for Chaitanya

1. **Which design system wins?** Brutalist vs legacy fv-* — or a hybrid?
2. **Are the `landing-page-editor/` components still needed?** They appear to be the standalone route version while `launch/` serves the overlay. Can the standalone route use the brutalist components?
3. **Ascent/peak variants in Refine** — these have their own bespoke CSS (`ra-*`, `rt-*`). Should these converge to brutalist or remain as a separate "narrative" design language within the chat?
4. **Panel headers** — Refine and Insight have none. Signal and Evidence have them. Should all five acts get a consistent header bar?
5. **Dark mode priority** — the `feat/dark-mode` branch is unshipped. Should dark-mode fixes be part of this unification or deferred?
