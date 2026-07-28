# Part 2 PR-2b Part A — ReportCanvas Migration Survey

**Date:** 2026-07-27  
**Branch:** `feat/universal-chat-tools` @ `857277a`  
**Mode:** Read-only. `npx tsc --noEmit` baseline only.  
**Prior:** `design-consistency-survey.md`, `p2-pr1-insight-signal-panelheader-survey.md`, `p2-pr2-evidence-report-side-survey.md`, `loading-flash-survey.md`, `p2-pr4-launch-dedup-survey.md`. Not re-audited here.

**LOC (line counts on disk):** ReportCanvas 815 · report-canvas.css 428 · ReportScoreSection 253 · report-score-section.css 311 · ValidationReportExportMenu 106 → **~1913** total.

**Live consumer:** `ChatInterface.tsx` L16, L1144–1151 only.

---

## 1. Component internal structure

### `ReportCanvas` JSX skeleton (regions)

```
div (shell: fullscreen fixed | h-full; fv-bg)
  [embedded toolbar] ExportMenu + Full screen          // embedded && !fullscreen
  [overlay header] Back(mobile) | title | Export | FS | Close
  div (scroll)
    LoadingState | ErrorBanner
    article.report-canvas-article
      header.report-masthead (eyebrow, title, recommendation badge, stat pills)
      ReportScoreSection
      nav.report-section-nav (anchor chips)
      section Recommendation → report-card
      section Executive summary → report-card
      section Research findings → expand/collapse questions → FindingCard(s)
      section Competitors → competitor cards grid
      section Market signals → signal blocks in card
      section Risk assessment → RiskAssessmentContent
      section Research limitations → prose card
      section Sources → numbered list + SafeCitationLink
      footer note (rubric version)
```

### File-local helpers (same module, not separate files)

| Helper | Role |
|--------|------|
| `SafeCitationLink` | http(s)-only external link |
| `ReadableProse` | `splitReadableParagraphs` → paragraphs |
| `RiskAssessmentContent` | structured risk list vs plain prose |
| `CitationRefs` | `[n]` jump links to `#citation-n` |
| `FindingCard` | claim + evidence + confidence badge |
| Class helpers | `recommendationBadgeClass`, `confidenceClass`, `findingAccentClass` |
| Data helpers | `collectAllCitations`, `buildCitationIndexMap`, `countFindings` |

**External subcomponents:** `ReportScoreSection`, `ValidationReportExportMenu`, `LoadingState`, `ErrorBanner`.

### Factoring verdict

**Monolith with several inline helpers**, not a deep composition tree. Score panel and export menu are already split. The main file is one scrollable article with repeated `report-block` / `report-card` patterns.

**Worth in-place rewrite** of `ReportCanvas` + restyle of the two siblings. Decomposition that would help (optional, not required for ship):

1. Keep `FindingCard` / `SafeCitationLink` as file-local or extract only if a second consumer appears.  
2. Do **not** merge into Evidence TipTap surfaces — different product (read-only validation report vs edited_doc).  
3. Chrome header could later use `PanelHeader` (`minimal` / `default`) instead of custom sticky fv header — opportunistic, not blocking.

---

## 2. CSS surface

### `report-canvas.css`

- Opens with comment `/* Validation report — readable editorial layout */`.  
- Root: `.report-canvas-article` sets `--report-prose-width` and `color: var(--fv-text)`.  
- Major regions: masthead, stats/pills, section nav, blocks/cards, questions, findings, competitors, risks, sources, recommendation badges, confidence (via global `fv-confidence-*` classes referenced from TSX).  
- **~50** unique top-level class selectors (grep count).

### `report-score-section.css`

- Comment: keep in sync with `lib/report-score-section-export-css.ts` for HTML downloads.  
- Root: `.report-score-panel` (1px border, `border-radius: 1rem`, fv surface).  
- Regions: grid cards, overall bar, chevron, detail panel, tone/fill strong|mixed|weak.  
- **~49** unique top-level class selectors.

### Scoping / conflict risk

- **Global CSS** via side-effect `import "./report-canvas.css"` / `"./report-score-section.css"` — not CSS modules.  
- Naming is **BEM-ish** (`report-*`, `report-score-*`).  
- **Conflict risk:** HTML export embeds parallel CSS (`validation-report-html-styles.ts`, `report-score-section-export-css.ts`) that reuses the **same class names**. In-app Tailwind/brutalist rewrite does **not** auto-update download appearance unless export CSS is updated in a follow-on (or deliberately left fv for offline HTML).  
- No print rules in the two component CSS files. Print styles live in **export** CSS (`validation-report-html-styles.ts` `@media print` with `#fff` / `#111`).

### Visual vs scaffolding

| Kind | Examples |
|------|----------|
| Visual patterns | masthead gradient, recommendation badges, finding left accents, confidence badges, score tone colors, cards with radius/1px borders |
| Layout scaffolding | `.report-block`, flex/grid for competitors/scores, sticky nav, spacing on article |

---

## 3. Score section behaviors

`ReportScoreSection` receives `report`, `sections: SectionScore[]`, `overall: number`, `derived?: boolean` (from `resolveReportScores`).

**Renders:**

- Header “Validation scores” + derived note (“Estimated from evidence · ” if `derived`).  
- Grid of **section** score cards (label, numeric score, progress bar, chevron).  
- **Overall** score button (larger bar).  
- On select: **detail panel** — rationale, supporting signals / caveats lists, context from report; close via X or re-toggle.

**Interactive:** click to expand/collapse detail (`selectedId` local state). Hover styles on cards (CSS). No hover-only popover; no drilldown beyond the detail panel.

**Data shape** (`ValidationReport` / `SectionScore` in `lib/types.ts`):

```491:542:frontend/lib/types.ts
export interface SectionScore {
  section_id: "market" | "competition" | "distribution" | "regulatory" | "risk" | "research";
  label: string;
  score: number;
  rationale?: string | null;
  pros?: string[];
  cons?: string[];
}
// ...
  section_scores?: SectionScore[];
  overall_score?: number | null;
```

`resolveReportScores` returns stored scores or **derived** estimates (`derived: true`). Detail copy built via `buildSectionScoreDetails` / `buildOverallScoreDetail`.

**Dynamic style:** score bar fill `style={{ width: \`${score}%\` }}` + `scoreTone` → `report-score-fill-{strong|mixed|weak}` / `report-score-tone-*`.

---

## 4. Export menu behaviors

`ValidationReportExportMenu`:

- Toggle button → absolute dropdown (`role="menu"`).  
- **Outside click** (`mousedown` on document) and **Escape** close menu.  
- No arrow-key focus trap / roving tabindex.  
- Formats: **HTML** and **Markdown** only (`downloadValidationReportHtml`, `downloadValidationReportMarkdown`).  
- **No** preview or confirm — click downloads immediately.

**Lib exports** (`lib/validation-report-export.ts`):

- `buildValidationReportHtml`  
- `downloadValidationReportHtml`  
- `buildValidationReportMarkdown`  
- `downloadValidationReportMarkdown`

---

## 5. Report content primitives inventory

| Primitive | In ReportCanvas / score | Brutalist equivalent elsewhere? |
|-----------|-------------------------|----------------------------------|
| Sticky chrome header | Custom fv header | **Match:** `PanelHeader` (`ui/PanelHeader.tsx`) — Signal uses it |
| Section headers + icon | `.report-block-title` | Partial: Signal/Evidence mono uppercase headings — **inline patterns**, no shared component |
| Dividers / block spacing | `.report-block`, borders | Pattern: `border-2 border-border-master` cards — **no shared ReportSection** |
| Score displays | `ReportScoreSection` | **Miss** — Signal has no numeric score bars |
| Finding / evidence cards | `FindingCard` | **Near-match:** `SignalInsightReport` `TakeawayCard` (claim + confidence badge, brutal card) |
| Recommendation badge | proceed/iterate/pivot/kill | **Match:** `SignalInsightReport.recommendationBadgeClass` (semantic status tokens) |
| Confidence pill | `fv-confidence-*` | **Match:** `SignalInsightReport.confidenceBadgeClass` |
| Citation links | `SafeCitationLink` + `[n]` refs | **Near-match:** `EvidenceSourcesBook` safe http(s) links — domain-grouped, not numbered |
| Citation hover **popover** | **Does not exist** — `title=` only | Miss — no popover primitive |
| Quote blocks | None distinct | n/a |
| Tables | None | n/a |
| Expand/collapse | Question accordion + Expand all | Pattern only in this file; Evidence TipTap is different |
| Empty states | Implicit (omit sections) | EvidenceSourcesBook empty card — pattern only |
| Loading | `LoadingState` (legacy spinner) | **Near:** `BrutalistSkeleton` — different API |
| Error | `ErrorBanner` (legacy) | Signal/Evidence often mono `text-status-critical` cards |
| Stat pills | masthead counts | Dashboard/Signal pills — not shared |
| Competitor cards | grid of cards | Miss as shared primitive |
| Risk structured list | `RiskAssessmentContent` | Miss |
| Export dropdown | fv menu | Miss as brutalist menu (restyle in place) |

---

## 6. Extraction candidates

| Candidate | Verdict |
|-----------|---------|
| Report section card (2px / brutal shadow) | **Inline in ReportCanvas** for PR-2b; extract to `ui/` when a second report-like consumer needs it |
| Score display (number + bar + tone) | **Keep inside `ReportScoreSection`** — unique to validation scores; export HTML still depends on class parity |
| Citation link + hover popover | Popover is a **miss today**; **do not invent** in PR-2b unless product asks. Keep `SafeCitationLink` behavior. Extract only if Evidence + Report share one component |
| Confidence pill | **Worth shared helper** (or copy Signal’s `confidenceBadgeClass` mapping) — second consumer already exists (`SignalInsightReport`). Prefer small shared util / tiny component over duplicating triad again |
| Recommendation badge | Same as confidence — **reuse Signal mapping pattern** (inline or tiny shared helper) |

---

## 7. Hardcoded color hazards

**TSX (five files):** no hits for `rgba(`, `#000`, `#fff`, `text-white`, `text-black`, `bg-white`, `bg-black`, `text-red-*` / blue / purple / green / yellow.

**`report-canvas.css`:** `color-mix(in srgb, white N%, transparent)` at L69, L93, L137, L225 (stat pills, question score, section link / related surfaces). Token-based otherwise (`var(--fv-*)`).

**`report-score-section.css`:** `color-mix(..., white …)` at L62, L282, L325; L322 is `white-space: pre-wrap` (not a color). Score fills use `--fv-success` / `--fv-warning` / muted — not Tailwind palette classes.

**Related (export, out of the five files but migration-adjacent):** `validation-report-html-styles.ts` print block uses `#fff`, `#111`, `#ddd`.

---

## 8. Refine chat integration

```1144:1152:frontend/components/chat/ChatInterface.tsx
      {canvasOpen && resolvedExperimentId && (
        <div className="fixed inset-0 z-[60] flex min-h-0 flex-col overflow-hidden border-l border-[var(--fv-border)] bg-[var(--fv-bg)] fv-msg-enter lg:relative lg:z-auto lg:min-h-0 lg:flex lg:min-w-0 lg:flex-1 lg:overflow-hidden">
          <ReportCanvas
            experimentId={resolvedExperimentId}
            projectName={projectName || "Validation report"}
            onClose={() => setCanvasOpen(false)}
            mobile
          />
        </div>
      )}
```

**ChatInterface owns:** `canvasOpen` (opened ~L838), `resolvedExperimentId`, `projectName`. Wrapper div owns fullscreen-on-small / side-pane-on-`lg+` layout — **not** `ReportCanvas.mobile`.

**Props into ReportCanvas:** `experimentId`, `projectName`, `onClose`, `mobile` (always `true` from this mount). `embedded` unused here (defaults false).

**Callbacks back:** only `onClose`. Report fetches its own data via `getValidationReport(experimentId)`.

**`mobile` inside ReportCanvas:** gates the **Back** button (`lg:hidden`) when `onClose && !fullscreen`. Does not change article layout, columns, or typography. Fullscreen / body scroll lock are independent of `mobile`.

---

## 9. Test surface

| Asset | Relation |
|-------|----------|
| Component `*.test.*` for the five files | **None** |
| Snapshot tests | **None** found |
| `lib/__tests__/report-text.test.ts` | Tests `parseRiskAssessment` / `splitReadableParagraphs` — helpers ReportCanvas **calls**. Contracts of helpers, not ReportCanvas UI |
| `lib/__tests__/parse-citations.test.ts` | Chat/Evidence citation parsing — **not** imported by ReportCanvas |

PR-2b restyle should not break these unit tests unless helpers change.

---

## 10. Migration risk assessment

**External deps from ReportCanvas:**

- `getValidationReport`  
- `lib/report-text` (`parseRiskAssessment`, `questionDisplayIndex`, `splitReadableParagraphs`)  
- `resolveQuestionScore` / `resolveReportScores`  
- `ValidationReportExportMenu` → export lib  
- `ReportScoreSection` → score-details + scoreTone  
- `LoadingState` / `ErrorBanner`  
- Global CSS class names (and export CSS class name coupling)

**Silent behavior risks from styling:**

- Score bar **width %** and tone classes must remain wired or bars read wrong.  
- Finding accent / confidence class swaps must preserve high/medium/low meaning (Signal already documents triad mapping).  
- Changing in-app CSS class names **without** updating `report-score-section-export-css.ts` / HTML builder leaves downloads looking “old” (acceptable if intentional).  
- Escape / fullscreen / body overflow / accordion state are React — styling-safe.

**Inline / dynamic styles:** score fill `width: ${score}%` only. Risk card uses `border-[color-mix(...--fv-warning...)]` Tailwind arbitrary.

**Print in the five files:** none. Print only on HTML export stylesheet.

---

## 11. Size sanity check

| Approach | Constructive estimate |
|----------|----------------------|
| In-place TSX restyle + replace/delete two CSS files with Tailwind | ~800–1200 LOC edited in ReportCanvas/score/export menu; **−739** CSS LOC deleted or largely unused |
| Plus optional PanelHeader / shared confidence helper | +small |
| Full decomposition into many new ui/* files | **>2000** constructive — not justified by Section 1 |

**Verdict:** **Single PR.** Stay under ~2000 constructive by rewriting in place, deleting (or emptying) the two CSS files for in-app use, and treating HTML export CSS sync as **explicit sub-scope** (either update export CSS in same PR or document deferred visual drift for downloads).

---

## 12. Baseline

```
857277a Part2 PR-4: delete landing-page-editor/, dedup Launch on brutalist launch/ tree
a076af9 Loading flash fix: unify auth, add loading.tsx per route, three-state auth machine
92bfdf2 Part2 PR-2a: delete Evidence report-side orphans
```

`npx tsc --noEmit`: **clean** (`TSC_EXIT:0`).
