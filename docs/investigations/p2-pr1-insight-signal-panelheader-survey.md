# Part 2 PR-1 Part A — Insight Migration + Signal Dedup + PanelHeader Survey

**Date:** 2026-07-27  
**Branch:** `feat/universal-chat-tools` @ `4fa2317`  
**Mode:** Read-only. No edits, commits, or server runs beyond `tsc --noEmit`.  
**Prior:** `docs/investigations/design-consistency-survey.md` (two-system north-star). This doc does not re-audit the full design system.

---

## 1. Insight surface inventory

| File | LOC | Export | Purpose | System today |
|------|-----|--------|---------|--------------|
| `frontend/components/insight/InsightStagePanel.tsx` | 63 | `InsightStagePanel` | Act shell: paywall unlock → report → decision when `INSIGHT_READY`; loading when `INSIGHT_GENERATING` | fv-* wrappers (`LoadingState`) |
| `frontend/components/insight/InsightReportViewer.tsx` | 212 | `InsightReportViewer` | `GET` insight report UI (recommendation, traffic, takeaways, conversion, “what would change”) | fv-* (`fv-section-card`, `badge-*`, `fv-confidence-*`, `rounded-xl`) |
| `frontend/components/insight/DecisionPanel.tsx` | 158 | `DecisionPanel` | Four-way founder decision; **archives** via `archiveExperiment` | fv-* (`fv-section-card`, `fv-btn-primary/ghost`) |
| `frontend/components/insight/MetricsStagePanel.tsx` | 117 | `MetricsStagePanel` | Metrics-stage shell (paywall + `MetricsWidget` + distribute) — **not Act 5 report/decision** | fv-* |
| `frontend/components/insight/MetricsWidget.tsx` | 346 | `MetricsWidget` | Live analytics + generate-insight CTA | fv-* |

**Consumers (every import of `insight/*`):**

| Consumer | Imports | Notes |
|----------|---------|--------|
| `dashboard/ExperimentDetailPanel.tsx` L24–25, L569, L584 | `InsightStagePanel`, `MetricsStagePanel` | Only consumer of both stage panels |
| `insight/InsightStagePanel.tsx` | `DecisionPanel`, `InsightReportViewer` | Internal |
| `insight/MetricsStagePanel.tsx` | `MetricsWidget` | Internal |

**No other imports** of `InsightReportViewer`, `DecisionPanel`, `InsightStagePanel`, or `Metrics*` from chat, Signal, Launch, or app routes.

**Orphan path:** `ExperimentDetailPanel` has **zero importers** elsewhere in `frontend/`. Live product path for Evidence/Launch/Signal is canvas `DeepDiveOverlay` — not this dashboard stage panel. Insight Act 5 UI that founders actually see today is Signal’s copies (see §2 / §6).

---

## 2. Signal Insight/Decision duplicates

### Imports + top structure

**`SignalInsightReport.tsx`** (248 LOC) — top:

```1:18:frontend/components/signal/SignalInsightReport.tsx
"use client";

import { useEffect, useState } from "react";
import { BarChart3, Brain, Lightbulb, Loader2, Sparkles, TrendingUp } from "lucide-react";
import { getInsightReport } from "@/lib/api";
// ...
/**
 * Port of `components/insight/InsightReportViewer` for Signal Verdict.
 * Owns GET /insight-report. Do not import from components/insight/ (dies in cleanup PR).
 */
```

Same data shape / section order as `InsightReportViewer`; brutalist chrome (`border-2 border-border-master`, `shadow-brutal-*`, `font-headline` / `font-label-md`). Loading/error are inline brutal cards, not `LoadingState` / `ErrorBanner`. Recommendation badges use semantic status tokens (comment: preserves proceed/iterate/pivot/kill meaning). Confidence badges: semantic tokens (comment: same triad as `fv-confidence-*`).

**`SignalFounderDecisionPanel.tsx`** (418 LOC) — top:

```1:11:frontend/components/signal/SignalFounderDecisionPanel.tsx
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  ApiError,
  getExperiment,
  recordFounderDecision,
  type FounderDecisionResponse,
} from "@/lib/api";
```

```93:96:frontend/components/signal/SignalFounderDecisionPanel.tsx
/**
 * Founder Signal decision — persists via PUT /founder-decision.
 * Does not archive. Amendable with CAS on founder_decision_version.
 */
```

### Behavioral vs cosmetic

| Concern | Insight `DecisionPanel` | Signal `SignalFounderDecisionPanel` |
|---------|-------------------------|-------------------------------------|
| Persist API | `archiveExperiment(id, decision)` | `recordFounderDecision` (`PUT /founder-decision`) |
| Archives? | Yes (pivot/kill copy says archives) | **No** — kill copy: “does not archive”; pivot: “archive separately” |
| Note field | No | Yes (`NOTE_MAX` 500) |
| Amend / recorded state | No — one-shot | Yes — recorded summary + Amend |
| CAS / 409 | No | Yes — `base_version`, conflict refresh via `getExperiment` |
| Archived UX | N/A | Read-only empty or recorded |
| Props | `experimentId`, `onDecision` | `experimentId`, `archived`, initial decision/at/note/version, `onRecorded` |

| Concern | Insight `InsightReportViewer` | Signal `SignalInsightReport` |
|---------|------------------------------|------------------------------|
| API | `getInsightReport` | Same |
| Sections | Same five blocks | Same |
| Styling | fv-* | Brutalist port |
| Loading/error | Shared UI | Inline brutal |

**Cosmetic drift on report:** badges/cards/typography only. **Decision is not a cosmetic port** — different endpoint and product behavior.

### Consumers of Signal duplicates

| File | Lines |
|------|-------|
| `signal/SignalVerdictReady.tsx` | imports L5–6; render L86, L88–96 |

No other consumers.

---

## 3. PanelHeader — “consistent slot” today

| Surface | File + lines | Structure | System | Behavior |
|---------|--------------|-----------|--------|----------|
| **Refine** | `RefineStagePanel.tsx` L18 | No act header — chat only | fv-* shell (`rounded-xl border`) | — |
| **Evidence** | `EvidenceStagePanel.tsx` L104–116 | Pinned recommendation badge only (not phase/title) | brutalist badge | Shrink-0 above scroll body |
| **Evidence chat** | `EvidenceChatPane.tsx` L698–701 | Title only: “Chat with report” | brutalist `border-b-2` | Shrink-0 |
| **Launch** | `LaunchTabs.tsx` L23–47 | Tab strip (Copy/Design/Share/Kit) as chrome | brutalist | Mode-switching tabs |
| **Launch kit fallback** | `LaunchStagePanel.tsx` `KitShell` L313–316 | Micro-copy only | brutalist sticky bar | No title actions |
| **Signal** | `SignalStagePanel.tsx` L189–196 | Phase label `Phase 05 · Signal` + title `Metrics + verdict` | brutalist sticky `border-b-2 bg-surface-elevated` | Sticky top of scroll column |
| **Signal verdict ready** | `SignalVerdictReady.tsx` L39–75 | Badge “Ready” + title + regenerate action | brutalist `border-b-2` | Actions in header row |
| **Insight** | `InsightStagePanel.tsx` | **None** | — | — |
| **DeepDive overlay** | `DeepDiveOverlay.tsx` L179–216+ | Back link + act title (“Phase 04: Launch” or `{act} deep-dive`) + Launch actions (Copy/Republish/Publish) + Archive | brutalist | Sticky overlay chrome; Launch-specific actions |
| **Universal chat dock** | `UniversalChatDock.tsx` L256–276 | Title “Fivvle” + collapse / disabled fullscreen | Mixed: brutalist shell, `border-b border-[var(--fv-border)]` header | Collapse toggle |

**Smallest prop superset** that covers the above + minimal:

- `variant?: "default" | "minimal"`
- `phaseLabel?: ReactNode` (e.g. `Phase 05 · Signal`)
- `title?: ReactNode`
- `badge?: ReactNode` (Ready / recommendation chip)
- `actions?: ReactNode`
- `breadcrumb?: ReactNode` (← Back — or leave on DeepDive only)
- `sticky?: boolean` (default true for act bars)
- `className?: string`

`minimal` / empty props → near-zero chrome (Insight/Refine first consumer of the slot without forcing title).

---

## 4. Primitives Insight actually needs

From `InsightReportViewer` + `DecisionPanel` (+ shell loading/error):

| Primitive | Insight usage | Brutalist equivalent already? |
|-----------|---------------|-------------------------------|
| Section card | `fv-section-card` | **Pattern in place:** `SignalInsightReport` sections (`border-2 … shadow-brutal-md`) — extract or copy pattern |
| Nested metric card | `rounded-xl border var(--fv-border)` | Same file: elevated brutal cards — copy pattern |
| Section heading | `text-lg font-semibold` | `font-headline text-headline-md uppercase tracking-tighter` — pattern, not component |
| Panel label | `fv-panel-label` | `font-label-md text-label-sm uppercase tracking-wider` — pattern |
| Recommendation badge | `badge-proceed` etc. | `recommendationBadgeClass` in `SignalInsightReport` — **copy-from**, extract if shared |
| Confidence badge | `fv-confidence-*` | Signal confidence classes — **copy-from** |
| Source-type pill | hardcoded purple/indigo | Signal uses border/status tokens — **copy-from** |
| Primary / ghost / danger buttons | `fv-btn-primary/ghost` | Signal decision grid + yellow CTAs — **copy-from**; no shared `BrutalistButton` |
| Loading | `LoadingState` (spinner) | Signal inline `Loader2` + mono uppercase — either keep shared or match Signal |
| Error | `ErrorBanner` (`fv-error`) | Signal alert card — **new-extraction or adopt ErrorBanner restyle later** |
| Icon tile (Sparkles box) | rounded accent mute | Signal yellow square `border-2 bg-brutalist-yellow` — pattern |
| Confirm destructive panel | danger border/bg | Signal `border-status-critical` block — pattern |

**Already extracted under `ui/`:** `BrutalistSkeleton` only (rounded-md — note radius vs sharp Signal cards). `EmptyState` / `ErrorBanner` / `LoadingState` are fv-*-era.

**PR-1 opportunistic extract (as Insight needs):** section card + recommendation/confidence badge helpers most likely; full button kit only if Decision migration forces it.

---

## 5. Hardcoded color hazards (touched surfaces)

| File | Line | What |
|------|------|------|
| `insight/DecisionPanel.tsx` | 109 | `hover:bg-red-500` on confirm |
| `insight/DecisionPanel.tsx` | 142 | `border-[rgba(239,68,68,0.3)]`, hover `0.5`, `hover:text-red-300` |
| `insight/InsightReportViewer.tsx` | 53 | `bg-purple-500/15 text-purple-300 ring-purple-500/30` (BEHAVIORAL) |
| `insight/InsightReportViewer.tsx` | 57 | `bg-indigo-500/15 text-indigo-300 ring-indigo-500/30` (SYNTHESIZED) |

**Signal** `SignalInsightReport` / `SignalFounderDecisionPanel`: **no** `rgba(` / `text-red-` / `bg-black` / `text-white` hits in that folder grep.

Act headers sampled (Signal stage, Evidence chat, Launch tabs, DeepDive bar): semantic / brutalist tokens — no rgba list hits in those header lines.

---

## 6. Insight route / entry points

| Entry | Path | Import |
|-------|------|--------|
| **Live:** Canvas DeepDive → Signal verdict ready | `ExperimentCanvas` → `DeepDiveOverlay` L266 → `SignalStagePanel` → `SignalVerdictReady` L86–96 | `@/components/signal/SignalInsightReport`, `SignalFounderDecisionPanel` |
| **Orphan:** Dashboard detail stage `"insight"` | `ExperimentDetailPanel` L582–588 | `@/components/insight/InsightStagePanel` |
| Standalone `/insight` route | **None found** | — |

DeepDive `act` union is `"evidence" | "launch" | "signal"` only — no separate Insight act tab. Insight report is a **Signal verdict substate**, not its own overlay act.

---

## 7. Behavioral / interaction concerns

- **Clipboard / PDF / print / share** on insight surface: **none** in `insight/` (no matches). Regenerate / paywall live on Signal (`useSignalGenerateInsight`, credits on control).
- **Decision persistence (live):** `PUT /experiments/{id}/founder-decision` via `recordFounderDecision` — CAS `base_version`; state in `SignalFounderDecisionPanel` + canvas experiment props. **Must keep.**
- **Decision persistence (orphan Insight panel):** `archiveExperiment` — different product path; not what Signal uses.
- **Motion:** `fv-msg-enter` on Insight confirm panel; `Loader2 animate-spin` / `enabled:hover:-translate-y-0.5` on Signal — decorative, not threshold logic.
- **Paywall:** `InsightStagePanel` uses `InsightUnlockPrompt` / wallet unlock; Signal generate path uses `useSignalGenerateInsight` + modal — separate gates.

---

## 8. Test surface

**Frontend** `*.test.*` / `*.spec.*`: **no** files touching Insight UI, Signal insight/decision, or founder-decision panels. Existing frontend tests: `parse-citations`, `ClarifyingQuestionBlock`, `report-text`, `launch-channel-intents` only.

**Snapshots:** none for this surface.

**Backend** (out of UI migration but related): `test_insight_prompt.py`, `test_insight_schemas.py`, `test_insight_threshold.py`, unarchive insight status — not frontend snapshot churn.

---

## 9. Size sanity check

| Chunk | LOC (approx) |
|-------|----------------|
| Insight Act 5 files (`InsightStagePanel` + `InsightReportViewer` + `DecisionPanel`) | ~433 |
| Signal duplicates (`SignalInsightReport` + `SignalFounderDecisionPanel`) | ~666 |
| `SignalVerdictReady` wiring | ~100 |
| New `PanelHeader` | ~80–120 |
| Opportunistic primitives | ~100–250 |
| **Subtotal in-scope** | **~1400–1600** |

Metrics files (~463) sit in `insight/` but are **metrics stage**, not this PR’s Act 5 report/decision pair — exclude unless scope expands.

**Verdict:** **~1500 LOC class** — upper end of “500–1500”; **flag for possible split** before implementation prompt (especially because decision dedupe is behavioral, not restyle-only).

---

## 10. Baseline

```
feat/universal-chat-tools
4fa2317 PR-4: cascade cleanup - v2 into cascade, delete phantom statuses, rename edited_doc staleness
cf363b6 PR-3: publish cohorts - isolate Signal analytics per publish
dd9585f PR-2: decouple public landing from status; wire Evidence edited_doc into Launch
e58a569 PR-1: cascade foundations - unify Spark writes, unblock refine reopen, add refined_idea_version dimension
b429381 feat(universal-chat): Kimi-primary tool loop with Anthropic fallback
```

`npx tsc --noEmit` (frontend): **exit 0**.

Working tree note: untracked `docs/investigations/design-consistency-survey.md` only (this survey file added when written).
