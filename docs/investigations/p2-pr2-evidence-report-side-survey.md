# Part 2 PR-2 Part A — Evidence Report-Side Migration Survey

**Date:** 2026-07-27  
**Branch:** `feat/universal-chat-tools` @ `8d2c56a`  
**Mode:** Read-only. `tsc --noEmit` only for baseline.  
**Prior:** `design-consistency-survey.md`, `p2-pr1-insight-signal-panelheader-survey.md`.

---

## Correction to Part 2 audit naming

Desktop **Evidence act** (DeepDive) does **not** mount `ReportCanvas` / `ValidationReport*`. It mounts `EvidenceStagePanel` → TipTap `EvidenceReportEditor` + chat + sources (already brutalist).

`ReportCanvas` is the **Refine chat** “Open report” surface (`ChatInterface`), with responsive layout (fullscreen on small screens; side pane on `lg+`). The `mobile` prop only toggles the back button (`lg:hidden`); the canvas itself is not mobile-only.

`frontend/components/report/` — **does not exist**.

---

## 1. `frontend/components/research/` inventory

| File | LOC | Export | Purpose | System |
|------|-----|--------|---------|--------|
| `EvidenceStagePanel.tsx` | 121 | `EvidenceStagePanel` | DeepDive Evidence shell: chat + editor + sources | Brutalist (+ `fv-skeleton` loading) |
| `EvidenceReportEditor.tsx` | 386 | `EvidenceReportEditor` | TipTap edited_doc editor | Brutalist |
| `EvidenceEditorToolbar.tsx` | 274 | toolbar | Formatting / save status | Brutalist |
| `EvidenceChatPane.tsx` | 916 | `EvidenceChatPane` | Report chat | Brutalist |
| `EvidenceSourcesBook.tsx` | 100 | `EvidenceSourcesBook` | Domain-grouped citations | Brutalist |
| `EditedDocOutdatedBanner.tsx` | 16 | `EditedDocOutdatedBanner` | edited_doc behind regen | Brutalist |
| `evidence-editor.css` | 70 | — | Editor prose styles | Editor-scoped |
| `ReportCanvas.tsx` | 815 | `ReportCanvas` | Read-only structured validation report UI | **fv-*** (+ CSS module) |
| `report-canvas.css` | 428 | — | Report canvas visual language (1px borders, radii) | **fv-*** |
| `ReportScoreSection.tsx` | 253 | `ReportScoreSection` | Score cards / overall score | CSS-driven (fv report scores) |
| `report-score-section.css` | 311 | — | Score section styles | fv report |
| `ValidationReportExportMenu.tsx` | 106 | `ValidationReportExportMenu` | HTML/MD download menu | fv-* (`fv-btn-ghost`, rounded dropdown) |
| `ValidationReportPanel.tsx` | 448 | `ValidationReportPanel` | Tabbed side-panel report | **fv-*** |
| `ValidationReportViewer.tsx` | 290 | `ValidationReportViewer` | Simple accordion report viewer | **fv-*** |
| `InlineResearchProgress.tsx` | 153 | `InlineResearchProgress` | In-chat research phase progress | fv-* |
| `ResearchProgress.tsx` | 93 | `ResearchProgress` | Standalone research progress card | fv-* |
| `PhaseIndicator.tsx` | 268 | `PhaseIndicator`, labels | Phase UI variants | fv-* |
| `ResearchActivityFeed.tsx` | 48 | feed | Activity lines for progress | fv CSS classes |
| `useResearchActivityLog.ts` | 101 | hook | Activity log state | n/a |
| `LandingGenerationProgress.tsx` | 144 | `LandingGenerationProgress` | Landing gen stage poll UI | fv-* |
| `TemplatePicker.tsx` | 89 | `TemplatePicker` | Landing template pick cards | fv-* |

Glob also listed `StalenessBanner.tsx` — **not on disk** (replaced by `EditedDocOutdatedBanner` in Part 1 PR-4).

---

## 2. Mount points / orphans

### Live

| Component | Importer | Notes |
|-----------|----------|--------|
| `EvidenceStagePanel` | `DeepDiveOverlay.tsx` ~L253 | Desktop Evidence act |
| `ReportCanvas` | `ChatInterface.tsx` L16, L1146–1151 | Refine “Open report”; always passes `mobile` |
| `InlineResearchProgress` | `ChatInterface.tsx` L15, L1064 | Research-in-progress in Refine chat |
| `ReportScoreSection` | `ReportCanvas`; also `ValidationReportPanel` | Live via canvas |
| `ValidationReportExportMenu` | `ReportCanvas` only | HTML/MD export |
| `PhaseIndicator` | `InlineResearchProgress`, `ResearchProgress`; labels via `lib/research-activity.ts` | |

### Orphans (zero importers outside self after PR-1 deleted `ExperimentDetailPanel`)

| Component | LOC | Note |
|-----------|-----|------|
| `ValidationReportPanel` | 448 | Was only self + scores |
| `ValidationReportViewer` | 290 | No importers |
| `LandingGenerationProgress` | 144 | Was ExperimentDetailPanel-only |
| `TemplatePicker` | 89 | Was ExperimentDetailPanel-only |
| `ResearchProgress` | 93 | No importers (`InlineResearchProgress` is the live path) |

**Filesystem:** `ExperimentDetailPanel.tsx` is gone (`Test-Path` false; `tsc` clean). Cursor/index greps may still ghost that path — treat as stale.

**Split input:** orphans are deletion candidates (PR-1 pattern), not migration work.

---

## 3. Desktop Evidence chrome (already brutalist)

| Component | Drift vs north star |
|-----------|---------------------|
| `EvidenceStagePanel` | Brutalist badge/error. Loading uses **`fv-skeleton`** (only soft fv remnant). No act `PanelHeader` — recommendation chip only (L107–116). DeepDive overlay supplies outer chrome. |
| `EvidenceReportEditor` / toolbar | Brutalist (out of PR-2 migrate scope unless drift). |
| `EvidenceSourcesBook` | Brutalist mono headings, `border-2 border-border-master`. |
| `EditedDocOutdatedBanner` | Brutalist yellow attention banner — clean. |

**PanelHeader:** Evidence stage does not use one today. Adopting would be optional (badge slot for recommendation / phase “EVIDENCE”); not required for report-viewer migration.

---

## 4. ChatInterface × ReportCanvas

```1144:1151:frontend/components/chat/ChatInterface.tsx
      {canvasOpen && resolvedExperimentId && (
        <div className="fixed inset-0 z-[60] ... lg:relative lg:z-auto ... lg:flex-1 ...">
          <ReportCanvas
            experimentId={resolvedExperimentId}
            projectName={projectName || "Validation report"}
            onClose={() => setCanvasOpen(false)}
            mobile
          />
```

- Layout: chat column hides on small screens when open; on `lg+` chat stays ~40% and canvas is a peer pane.
- `mobile` → back affordance `lg:hidden` (L442–450 in `ReportCanvas`).
- Visual language: **separate** from Evidence TipTap (fv report CSS: 1px borders, many `border-radius` values in `report-canvas.css`) — not a scaled Evidence editor.

**Mobile brutalist precedent:** Launch already uses full `border-2 border-border-master` on small viewports (e.g. `LivePagePreviewPanel`). No established “light brutalist” mobile variant.

---

## 5. Report content primitives (`ReportCanvas` family)

| Primitive | Where | Brutalist equivalent? |
|-----------|--------|------------------------|
| Sticky report header | `ReportCanvas` L440 | `PanelHeader` (PR-1) — **consume** |
| Score cards / overall | `ReportScoreSection` + CSS | New-extraction / rewrite pattern from Signal cards |
| Section / finding cards | `report-canvas.css` `.report-*` | Copy Signal `border-2 … shadow-brutal-*` pattern |
| Recommendation badges | CSS `badge-*` / classes | Copy `EvidenceStagePanel` / Signal recommendation tokens |
| Confidence pills | `fv-confidence-*` / rgba in orphans | Signal `confidenceBadgeClass` pattern |
| Citation links | `SafeCitationLink` in canvas/panel/viewer | `EvidenceSourcesBook` safe-link pattern |
| Expand/collapse questions | `ReportCanvas` local state | Behavior preserve; restyle chrome |
| Loading | `LoadingState` | Brutalist skeleton / mono spinner pattern |
| Error | `ErrorBanner` | Or Signal alert card / `text-status-critical` |
| Export menu | `ValidationReportExportMenu` | Restyle buttons to brutalist; keep download APIs |
| Masthead / prose | CSS | Rewrite to tokens |

No shared extracted “BrutalistCard” yet — PR-1 only shipped `PanelHeader` / `BrutalistSkeleton`.

---

## 6. Progress + templates

| Piece | Live? | In PR-2 report-consumption scope? |
|-------|-------|-----------------------------------|
| `InlineResearchProgress` + `PhaseIndicator` | Yes (Refine chat) | Adjacent fv-* progress; not report body. Audit rgba also in `PhaseIndicator` L217 |
| `LandingGenerationProgress` | **Orphan** | Deletion candidate; rgba L151 |
| `TemplatePicker` | **Orphan** | Deletion; Launch has `TemplatePanel` |
| `ResearchProgress` | **Orphan** | Deletion |

---

## 7. Hardcoded color hazards (report-side)

| File | Line(s) | Styles |
|------|---------|--------|
| `LandingGenerationProgress.tsx` | 151 | Divider `rgba(255,255,255,0.04)` |
| `PhaseIndicator.tsx` | 217 | Same divider rgba |
| `ValidationReportViewer.tsx` | 48–50, 59–65 | Confidence/recommendation rgba greens/ambers; kill `text-red-300` |
| `ValidationReportPanel.tsx` | 60–62, 255, 281, 325–326 | Confidence rgba; tab `borderColor: rgba(255,255,255,0.07)`; success tint box |

`ReportCanvas.tsx` / `report-canvas.css`: mostly `var(--fv-*)` / `color-mix` — fewer literal rgba, but **soft rounded fv language**, not brutalist.

---

## 8. Behavioral preserve

| Behavior | Where | Touch? |
|----------|--------|--------|
| HTML/MD export downloads | `ValidationReportExportMenu` → `lib/validation-report-export` | Keep call sites |
| Safe http(s) citation links | ReportCanvas / SourcesBook | Keep URL gate |
| Question expand/collapse + Escape / fullscreen body lock | `ReportCanvas` | Keep |
| Chat copy-to-clipboard | `EvidenceChatPane` (out of report migrate) | Don’t touch |
| Editor `scrollIntoView` for refs | `EvidenceReportEditor` | Don’t touch |
| Print-specific CSS on canvas | **None found** in ReportCanvas | — |

---

## 9. Tests

| File | Relation |
|------|----------|
| `lib/__tests__/report-text.test.ts` | Pure `report-text` helpers — no UI snapshots |
| `lib/__tests__/parse-citations.test.ts` | Citation parsing — not report UI |
| No `research/**/*.test.*` | — |

**Snapshots:** none for report UI.

---

## 10. Size sanity

| Slice | Approx LOC |
|-------|------------|
| **Orphan delete set** (Panel + Viewer + LandingGen + TemplatePicker + ResearchProgress) | ~**1064** |
| **Live ReportCanvas migrate** (tsx + canvas CSS + score section + score CSS + export menu) | ~**1913** |
| Evidence desktop editor/chat/sources (already brutalist) | Out of migrate scope |

**Verdict:** Live ReportCanvas family alone is **1500+** → **flag for split** (e.g. orphan deletion PR vs ReportCanvas brutalist rewrite). Orphan-only pass is ~1k LOC deletes, similar to PR-1 Insight orphan work.

---

## 11. Baseline

```
8d2c56a Part2 PR-1: delete orphaned Insight, extract PanelHeader, audit Signal to brutalist north star
4fa2317 PR-4: cascade cleanup - v2 into cascade, delete phantom statuses, rename edited_doc staleness
cf363b6 PR-3: publish cohorts - isolate Signal analytics per publish
dd9585f PR-2: decouple public landing from status; wire Evidence edited_doc into Launch
e58a569 PR-1: cascade foundations - unify Spark writes, unblock refine reopen, add refined_idea_version dimension
```

`npx tsc --noEmit` (frontend): **exit 0**.
