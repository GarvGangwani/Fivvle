# Part 2 PR-5 Part A — Straggler Sweep Survey

**Date:** 2026-07-28  
**Branch:** `feat/universal-chat-tools` @ `2998df6`  
**Mode:** Read-only. `npx tsc --noEmit` baseline only (exit 0).  
**Prior:** design-consistency + Part 2 PR-1…PR-4 / PR-3a/b surveys. Not re-audited here.

**Excluded by scope:** `.next/`, `node_modules/`, `__snapshots__/`, HTML export CSS (`validation-report-html-styles.ts`, `report-score-section-export-css.ts`), UniversalChatDock (own future PR).

---

## Load-bearing finding

PRs 1–4 cleaned Evidence / Signal / Report / Launch editor / Refine Stack A–B. **Large `fv-*` surfaces remain** outside those acts: wallet, settings, admin, research progress chrome, distribution, dual dashboard shell (`FivvleShell` still live), and shared UI primitives (`EmptyState`, `ErrorBanner`, `TypeConfirmDialog`, `ToastProvider`). Separately, **confirmed orphans** (~760 LOC) are safe delete candidates: floating-nav leftovers, `AppHeader`, `preview/device` + `device-preview-messages`, unused lib helpers.

---

## 1. `fv-*` remaining hits

### Token system / leave alone
| Location | ~hits | Notes |
|----------|-------|-------|
| `app/globals.css` | ~582 | `--fv-*` definitions + utility classes (`.fv-brutal-hover*`, phase bar, wallet, etc.) |
| `tailwind.config.ts` | ~50 | Maps brutalist Tailwind names → `var(--fv-*)` |

### Deferred by scope
| Bucket | ~hits | Notes |
|--------|-------|-------|
| UniversalChatDock | ~20 | Explicit PR-5 defer |
| HTML export CSS + `validation-report-export.ts` | ~170+ | Explicit defer |
| Landing-template CSS/TSX (`surface-overlay`, `SurfaceShell`, …) | dozens | Public template styling; not founder-dashboard chrome |

### Intentional keep — `fv-brutal-hover*`
Defined `globals.css` ~L648–682. Consumers (Stack A + canvas):  
`RefinedIdeaCard`, `RefineMCQPopup`, `ActNode`, `SparkNode`, `CoreShellNode`, `ProjectCard`, `AppSideRail` (orphan). Visually brutalist utilities — flag, don’t migrate as token debt.

### Stack A Refine — only intentional `fv-*`
Confirmed: **only** `fv-brutal-hover` / `fv-brutal-hover-glow` in `refine/` (+ same utilities on canvas nodes). No leftover `var(--fv-code-*)` / surface vars from PR-3a.

### Live product debt (highest signal)

| Area | Files (approx hit counts) | Pattern |
|------|---------------------------|---------|
| **Admin** | `AdminCostDashboard` (~85), `AdminCouponsDashboard` (~62) | Heavy `var(--fv-*)` + `PageHeader` consumer but fv chrome |
| **Wallet** | `BuyCreditsFlow` (~29), paywall modals (~22 each ×3), `WalletModal` (~12), prompts, `CouponRedemption`, `WalletTrigger` | `fv-btn-*`, `fv-wallet-*`, `var(--fv-text*)` |
| **Settings** | `SettingsPanel` (~27), `WalletTransactionHistory` (~30) | Overlay + fv tokens |
| **Layout shell (legacy)** | `ShellSidebar` (~40), `FivvleShell` (~12) | Still mounted via `layout/DashboardShell` for routes **outside** `BRUTALIST_ROUTES` |
| **Brutalist nav (mixed)** | `FloatingAppNav` (~15) | Border-master + many `var(--fv-*)` |
| **Research progress** | `PhaseIndicator` (~27), `InlineResearchProgress` (~12), `ResearchActivityFeed` (~9), `evidence-editor.css` (~4) | `.fv-phase-bar*`, `.fv-research-activity*`, `fv-skeleton` |
| **Distribution** | `DistributeSection` (~14), `ShareLinksPanel` (~6) | `fv-card`, fv text tokens |
| **Experiment chrome** | `EditableProjectName`, `ArchiveProjectDialog`, `ExperimentStageNav`, canvas edges / `ExperimentCanvas` stroke | `fv-input`/`fv-btn-*`, `var(--fv-canvas-edge)` |
| **Shared UI primitives** | `TypeConfirmDialog` (~10), `ToastProvider` (~5), `EmptyState` (~4), `ErrorBanner` (~3), `LoadingState`/`PageHeader` (~2) | Primitives adopted in PR-1/3a still **fv-styled** |
| **Launch leftovers** | `LivePagePreviewPanel` (2 — CSS vars for canvas bg), comments on slug editor | Comments note slug editor still fv-* |

Rough **live-product hit sum** (excluding globals, tailwind, export CSS, UniversalChatDock, landing-templates): **~500+ class/var references** across ~45 files — not a small polish pass.

---

## 2. Hardcoded color hazards (live product)

| Hit | File | What it styles | Classification |
|-----|------|----------------|----------------|
| `bg-black/60` | Wallet paywall modals ×4, `SettingsPanel`, `ArchiveProjectDialog`, `TypeConfirmDialog` | Modal scrim | Cosmetic drift vs semantic overlay token |
| `text-white` | `UniversalChatDock` send btn (deferred); orphan `AppHeader` | Inverse on accent / glass header | Dock deferred; AppHeader orphan |
| `border-white/10`, `bg-black/40`, `text-white` | `AppHeader.tsx` | Glass header | **Orphan file** |
| `rgba(...)` toast colors | `ToastProvider.tsx` L34–41 | Success/error toast bg/border | Cosmetic; not semantic status tokens |
| `#16A34A` / `#BA1A1A` | `tailwind.config.ts` status-* | Design tokens | Leave (token system) |
| Landing-template `#fff`/`rgba` | `aether`, `abstract`, etc. | Public LP visuals | Out of dashboard sweep; intentional template art |
| Export CSS `#fff`/`rgba` | deferred files | Print/HTML export | Deferred |

Few `text-red-*` / `text-gray-*` left in live app TSX after Refine `text-status-critical` fix. Palette Tailwind color classes are not a major dashboard residue vs `var(--fv-*)`.

---

## 3. Unmigrated reinvented primitives

| Pattern | File | Assessment |
|---------|------|------------|
| Custom loading bars (`animate-pulse` + `border-2 border-border-master`) | `LaunchCopyTab.tsx` ~L193–195 | Genuine **BrutalistSkeleton** miss |
| Custom pulse blocks | `ArchivedProjectsContent.tsx` ~L69–74 | Genuine skeleton miss (semantic tokens already) |
| `fv-skeleton` | `EvidenceReportEditor.tsx` ~L399 | fv class skeleton; candidate BrutalistSkeleton |
| Custom empty copy (not `EmptyState`) | `EvidenceChatPane.tsx` ~L709–714 | One-off mono empty — reasonable; or adopt EmptyState |
| Sticky toolbar wrapper | `EvidenceReportEditor.tsx` ~L404 | Editor toolbar sticky — **not** PanelHeader miss |
| Sticky TOC | `ReportCanvas.tsx` ~L608 | In-document sticky — reasonable one-off |
| Sticky shell chrome | `FivvleShell` / `ShellSidebar` | Legacy shell headers — migrate/delete with shell, not PanelHeader |
| `window.confirm` | `ExperimentCanvas` refine reopen (~L406); `useSparkManualSave`; `DeepDiveOverlay`; `AdminCouponsDashboard` ×2 | Native confirms remain; Refine reopen noted in PR-3a |
| Confirm dialogs | `BrutalistConfirm` (Refine-local); `TypeConfirmDialog` (still fv) | Consolidation still deferred |

`PanelHeader` consumers today: Signal, ReportCanvas, Refine expanded/fullscreen — good coverage for act panels.

---

## 4. Dead imports / unreferenced files

### Prior deletions — confirmed gone on disk
Zero live importers for `components/refinement`, `landing-page-editor`, `insight`, `ExperimentDetailPanel`. Paths do not exist.

### `components/chat/`
Only **`ChatMarkdown.tsx`** remains; consumed by UniversalChatDock. Clean.

### Confirmed orphans (delete candidates — note only)

| Path | ~LOC | Evidence |
|------|------|----------|
| `components/dashboard/AppTopNav.tsx` | ~55 | Comment: ORPHANED; only self-export + DashboardShell comment |
| `components/dashboard/AppSideRail.tsx` | ~102 | Same |
| `components/layout/AppHeader.tsx` | ~28 | **Zero** importers |
| `app/preview/device/page.tsx` + `layout.tsx` | ~88 | Only consumer of `device-preview-messages`; Launch preview uses `/e/{slug}` iframe, not this route |
| `lib/device-preview-messages.ts` | ~30 | Only imported by preview/device |
| `lib/device-presets.ts` | ~229 | Zero `@/lib/device-presets` importers |
| `lib/export-page.ts` | ~155 | Zero importers |
| `lib/insight-flow.ts` | ~25 | Zero importers |
| `lib/metrics-flow.ts` | ~15 | Zero importers |
| `lib/validation-flow.ts` | ~34 | Zero importers |

**Orphan delete budget ~760 LOC** if approved.

### Dual shell (not orphan — still live)
`layout/DashboardShell.tsx` L7–28: `BRUTALIST_ROUTES` → `dashboard/DashboardShell` (`FloatingAppNav`); else → **`FivvleShell` + `ShellSidebar`** (fv-heavy). Both shells remain in the product tree.

---

## 5. TODO / deferred markers

| Hit | Context |
|-----|---------|
| `DashboardShell.tsx` L11 | `AppTopNav + AppSideRail orphaned by feat/floating-nav — flag for cleanup PR.` |
| `AppTopNav.tsx` / `AppSideRail.tsx` file headers | `ORPHANED by feat/floating-nav` |
| `AppSideRail.tsx` L29 | `notifications feature deferred — tracked-work #33` |
| `PublishConfirmDialog.tsx` L37 | CTA mode picker deferred |
| `PublishConfirmDialog` / `StartupUrlCard` comments | Slug editor still fv-*; brutalist wrapper only |
| No matches | `TODO.*brutalist`, `TODO.*fv-`, `FIXME.*design` |

---

## 6. Stack A remaining hazards

**Only** intentional `fv-brutal-hover` / `fv-brutal-hover-glow` in Refine Stack A. No other `fv-*` in `experiment/refine/` after PR-3a.

---

## 7. `app/preview/device/` status

**Still orphaned.** No Launch/LivePagePreview (or other) consumer posts to `/preview/device`. Cascade: `lib/device-preview-messages.ts` (+ likely `lib/device-presets.ts` from old editor). **Delete candidate** — survey notes only; do not delete in PR-5 without confirmation.

---

## 8. Size sanity check

| PR-5 slice | Est. | Band |
|------------|------|------|
| Orphan deletes only (nav leftovers, AppHeader, preview/device, unused libs) | ~760 LOC deleted | Comfortable / normal |
| + skeleton/empty/scrim polish on already-brutalist surfaces | +100–300 | Still normal |
| + migrate wallet/settings/admin/FivvleShell/research progress `fv-*` | **2000+** | **Flag — split**; not a single “straggler” PR |

Highest-signal small sweep: **§4 orphans** + **§3 skeleton misses** + optionally shared UI primitive token pass. Full remaining `fv-*` is a Part 3–scale effort.

---

## 9. Baseline

```
2998df6 Part2 PR-3b: delete Stack B orphaned Refine narrative + supporting shells
a1d1653 Part2 PR-3a: polish canvas Refine (Stack A) to shared brutalist chrome
bcf3a5d Part2 PR-2b: migrate ReportCanvas / ReportScoreSection / ExportMenu to brutalist
```

`cd frontend && npx tsc --noEmit` → **exit 0**.

---

## Findings summary (no proposals)

1. **§1:** Token system + exports + dock aside, **~500+ live `fv-*` hits** remain — wallet/settings/admin/legacy shell/research progress dominate.  
2. **§3:** Clear skeleton misses (`LaunchCopyTab`, archived list, `fv-skeleton`); `window.confirm` still in Refine reopen + Spark/DeepDive/admin.  
3. **§4:** Prior orphan PRs clean; **new confirmed orphans** (~760 LOC) including `preview/device` and floating-nav leftovers.  
4. Stack A Refine is clean except intentional hover utilities.  
5. Full remaining `fv-*` migration is **800+ / split** territory; orphan+skeleton sweep fits a normal PR-5.
