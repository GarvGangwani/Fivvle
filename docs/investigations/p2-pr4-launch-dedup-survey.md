# Part 2 PR-4 Part A — Launch Dedup + landing-page-editor Deletion Survey

**Date:** 2026-07-27  
**Branch:** `feat/universal-chat-tools` @ `a076af9`  
**Mode:** Read-only. `npx tsc --noEmit` baseline only.  
**Prior:** `design-consistency-survey.md`, `p2-pr1-insight-signal-panelheader-survey.md`, `p2-pr2-evidence-report-side-survey.md`, `loading-flash-survey.md`. Not re-audited here.

---

## 1. Two-system inventory

### System A — delete side (`frontend/components/landing-page-editor/`)

| File | LOC | Export | Purpose |
|------|-----|--------|---------|
| `EditorLayout.tsx` | 850 | `EditorLayout` | Full fv-* standalone editor shell (content/design/publish + preview) |
| `CopyFieldsEditor.tsx` | 581 | `CopyFieldsEditor`, `CopySectionId` | Sectioned copy fields for System A |
| `DevicePreview.tsx` | 534 | `DevicePreview` | Device chrome + postMessage iframe preview |
| `device-preview.module.css` | 447 | — | Device preview / save-status styles |
| `editor-panel.css` | 643 | — | Editor chrome styles |
| `ColorThemePicker.tsx` | 345 | `ColorThemePicker`, `ThemePatch` | Palette picker (round swatches) |
| `LandingPageSlugEditor.tsx` | 289 | `LandingPageSlugEditor` | Slug availability + PATCH (fv-* UI) |
| `BrandIconPicker.tsx` | 227 | `BrandIconPicker`, `BrandingPatch` | Logo upload + icon/size controls |
| `SurfaceStylePicker.tsx` | 131 | `SurfaceStylePicker` | Surface / atmosphere controls |
| `TemplatePreviewThumb.tsx` | 100 | `TemplatePreviewThumb` | Live `TemplateRenderer` thumb for template pick |
| `LandingPagePreview.tsx` | 80 | `LandingPagePreview` | Wraps DevicePreview + TemplateRenderer |
| `DevicePreviewIframe.tsx` | 73 | `DevicePreviewIframe` | Posts payload to `/preview/device` |
| `CollapsibleSection.tsx` | 73 | `CollapsibleSection` | Rounded collapsible section |
| `PreviewSaveStatus.tsx` | 59 | `PreviewSaveStatus`, badge | pending/saving/saved/error badge |
| `DesignSlider.tsx` | 57 | `DesignSlider` | CSS-painted range slider |
| `EditorLoadingSkeleton.tsx` | 31 | `EditorLoadingSkeleton` | fv-skeleton full editor layout |

**System A total (ts/tsx/css):** ~**4520** LOC.

### System B — keep side (`frontend/components/launch/`)

| File | LOC | Export | Purpose |
|------|-----|--------|---------|
| `LaunchCopyTab.tsx` | 1094 | `LaunchCopyTab` | Copy edit + regen + 500ms autosave |
| `LaunchStagePanel.tsx` | 342 | `LaunchStagePanel`, `LaunchLandingReport` | DeepDive Launch shell (tabs + preview + kit) |
| `design/ColorThemePanel.tsx` | 291 | `ColorThemePanel` | Brutalist color picker |
| `design/LaunchDesignTab.tsx` | 290 | `LaunchDesignTab` | Design tab orchestrator + page autosave |
| `LaunchKitPanel.tsx` | 268 | `LaunchKitPanel` | Kit readiness + share copy variants |
| `design/BrandIconPanel.tsx` | 238 | `BrandIconPanel` | Logo upload + branding |
| `PublishConfirmDialog.tsx` | 200 | `PublishConfirmDialog` | Publish confirm + slug |
| `LivePagePreviewPanel.tsx` | 187 | `LivePagePreviewPanel`, `PreviewState` | Live iframe / draft placeholder |
| `ShareCopyEditor.tsx` | 143 | `ShareCopyEditor` | LaunchKit share-copy variants UI |
| `design/SurfaceAtmospherePanel.tsx` | 134 | `SurfaceAtmospherePanel` | Surface controls |
| `design/TemplatePanel.tsx` | 125 | `TemplatePanel` | Template pick (wireframe mocks) |
| `ChannelSelectPopover.tsx` | 114 | `ChannelSelectPopover` | First-channel picker |
| `share/StartupUrlCard.tsx` | 108 | `StartupUrlCard` | Slug card wrapping SlugEditor |
| `BrutalistEditableField.tsx` | 89 | `BrutalistEditableField` | Inline editable field |
| `share/LaunchShareTab.tsx` | 80 | `LaunchShareTab` | Share tab shell |
| `design/BrutalistSlider.tsx` | 60 | `BrutalistSlider` | Native + brutal badge slider |
| `design/DesignCollapsibleCard.tsx` | 56 | `DesignCollapsibleCard` | Brutalist collapsible |
| `LaunchTabs.tsx` | 45 | `LaunchTabs`, `LaunchTabId` | copy/design/share/kit tabs |
| `share/ShareWithTrackingCard.tsx` | 42 | `ShareWithTrackingCard` | Tracking share links card |

**System B total:** ~**3906** LOC.

### Editor-adjacent outside both dirs

| Path | Classify |
|------|----------|
| `components/landing-templates/*` | **Preserve** — templates + `SectionImageSlot`, `TemplateRenderer`, `EditableCopy`, `BrandMark`, `SurfaceShell` |
| `components/published/*` | **Preserve** — public `/e/[slug]` |
| `components/distribution/ShareLinksPanel.tsx` | **Shared** — used by A (EditorLayout) and B (Kit/Share) |
| `app/preview/device/*` | **Device preview host** — only System A `DevicePreviewIframe` posts here today |
| `lib/device-preview-messages.ts` | Messaging contract for device preview |
| `lib/landing-regen.ts` | Shared regen helper; comment still names EditorLayout |
| `components/research/TemplatePicker.tsx` | fv-* template cards; imports A’s `TemplatePreviewThumb` |
| `components/dashboard/ExperimentDetailPanel.tsx` | **Orphan** — mounts `EditorLayout`; no importers |
| `components/landing-runtime-v2/` | **Missing on disk** (context docs only) |
| `components/editor/`, `components/landing/` | **Do not exist** |

---

## 2. Consumer map

### Importers of System A (external)

| A export | Importer | Live? |
|----------|----------|-------|
| `EditorLoadingSkeleton` | `app/(dashboard)/experiment/[id]/landing-page/page.tsx` | **Yes** (redirect shim only) |
| `LandingPageSlugEditor` | `launch/PublishConfirmDialog.tsx`, `launch/share/StartupUrlCard.tsx` | **Yes** — System B depends on A |
| `EditorLayout` | `dashboard/ExperimentDetailPanel.tsx` | **No** — panel has zero importers |
| `TemplatePreviewThumb` | `research/TemplatePicker.tsx` | **No** — only via orphan detail panel |
| Remaining A files | Only intra-A / via `EditorLayout` | Dead with orphan |

### Importers of System B (external)

| B export | Importer |
|----------|----------|
| `LaunchStagePanel`, `PublishConfirmDialog` | `experiment/deep-dive/DeepDiveOverlay.tsx` |
| Internal B graph | Self-contained under `launch/` |
| Tests | `lib/__tests__/launch-channel-intents.test.ts` — tests **lib**, not `components/launch` UI |

### Routes / overlays

| Surface | System |
|---------|--------|
| DeepDive Launch (`ExperimentCanvas` → `DeepDiveOverlay` → `LaunchStagePanel`) | **B** |
| `/experiment/[id]/landing-page` | Redirect to `?stage=landing`; skeleton from **A** only while redirecting |
| Orphan `ExperimentDetailPanel` | Would mount **A** `EditorLayout` if ever wired — currently unreachable |

Bimodal confirmed: live Launch = **B**; standalone editor route no longer hosts A editor — it redirects into canvas Launch.

---

## 3. Route entry points

### Pages that import editor components

**`app/(dashboard)/experiment/[id]/landing-page/page.tsx`**

```5:16:frontend/app/(dashboard)/experiment/[id]/landing-page/page.tsx
import { EditorLoadingSkeleton } from "@/components/landing-page-editor/EditorLoadingSkeleton";
// ...
  useEffect(() => {
    router.replace(`/experiment/${experimentId}?stage=landing`);
  }, [experimentId, router]);
  return <EditorLoadingSkeleton />;
```

**Journey:** legacy bookmark/link → skeleton → soft-nav to canvas with Launch stage.

**`app/(dashboard)/experiment/[id]/page.tsx`** — no direct landing-editor import; mounts canvas → DeepDive → **B**.

**Journey:** dashboard / ProjectCard → `/experiment/[id]` → open Launch act → DeepDive Overlay → `LaunchStagePanel`.

**`app/e/[slug]/page.tsx`** — `PublishedLandingPage` only (not an editor).

**`app/preview/device/page.tsx`** — TemplateRenderer host for A’s iframe; not a founder editor route.

No other `app/**/page.tsx` imports `landing-page-editor/*` or `launch/*`.

---

## 4. Behavioral diff (load-bearing)

Paired surfaces:

| Concern | System A | System B |
|---------|----------|----------|
| Shell | `EditorLayout` tabs content/design/publish | `LaunchStagePanel` tabs copy/design/share/kit |
| Copy UI | `CopyFieldsEditor` | `LaunchCopyTab` |
| Design UI | Color/Brand/Surface pickers + CollapsibleSection | `*Panel` + `DesignCollapsibleCard` |
| Template | `TemplatePreviewThumb` (live render) | `TemplatePanel` (wireframe) |
| Preview | `LandingPagePreview` → DevicePreview → live draft `TemplateRenderer` (+ optional `/preview/device` iframe) | `LivePagePreviewPanel`: live = `/e` iframe + `cacheBust`; draft = placeholder card (“Publish to preview”) |
| Slug | `LandingPageSlugEditor` (also consumed by B) | Same component via B wrappers |
| Publish | Inline `publishProject` in EditorLayout | `PublishConfirmDialog` (modal) |
| Kit / share variants | ShareLinksPanel only on publish tab | `LaunchKitPanel` + `ShareCopyEditor` (variants) — **B-only product surface** |

### Autosave

| | A (`EditorLayout.persistPatch`) | B (`LaunchCopyTab` / `LaunchDesignTab`) |
|--|--------------------------------|----------------------------------------|
| Debounce | **500ms** | **500ms** |
| Abort | `AbortController` per save | same |
| Dirty UI | `PreviewSaveStatus`: pending → saving → saved (2.5s) → idle; error detail string | boolean `saving`; toast on failure |
| Rollback | No local rollback on fail | Restores snapshot copy/page (or page/template) on fail |
| Payload | Often copy+page+template together | Copy tab: copy+page; Design: page (+ template_id on switch) |
| Caps | Not gated in persistPatch | Copy tab blocks persist if `copyExceedsCaps` |
| CAS / version | Neither path sends If-Match / version headers in these components |

### File uploads

| | A | B |
|--|---|---|
| Logo | `BrandIconPicker` → `uploadProjectLogo` + uploading/error UI | `BrandIconPanel` → same API |
| Section / hero images | Wired: `EditorLayout.handleSectionImageChange` → preview `TemplateRenderer` → `SectionImageSlot` → `uploadSectionImage` | **No** design/copy tab wiring of `onSectionImageChange`; section image UX only exists on A’s draft preview path |
| Progress / errors | Local uploading flag + `text-red-400` (A) / mono critical (B logo) | Logo only on B |

### Preview refresh

- **A:** Local state drives `TemplateRenderer` immediately; DevicePreview posts UPDATE to iframe when using iframe mode; save status badge separate.
- **B:** After successful PATCH, `onLandingPageSaved` → `bumpPreviewCache` (`?v=` on live iframe). Draft never shows editable preview.
- Neither calls an explicit ISR revalidate API from these components.

### Unsaved-changes warning

- **Neither** system registers `beforeunload` or an in-app navigation dirty guard.

### Template selection

- Duplicated UIs (live thumbs vs wireframes). Not a shared component. Orphan `TemplatePicker` (research/) is a third fv-* picker used only by orphan detail panel.

### Publish flow

- Both hardcode `cta_mode: "waitlist"` (`EditorLayout` L260; `PublishConfirmDialog` L95–97 comment: backend ignores body; picker deferred).
- A: toast + `onPublished` callback in-layout.
- B: modal with slug editor + 3-line copy preview, then `publishProject`.

### Copy variants / regeneration

- **Share-copy variants:** **B only** (`ShareCopyEditor` + LaunchKit).
- **Section regen:** A has inline poll loop in `EditorLayout`; B uses shared `lib/landing-regen.ts` from `LaunchCopyTab` (comment still references EditorLayout).

### `cta_mode` UI

- No picker in A or B. Publish always sends `"waitlist"`. Public read: `PublishedLandingPage` / `lib/published-page.ts` consume `cta_mode` from API.

### Unique-to-A (not on live B)

1. WYSIWYG **draft** preview with device chrome.  
2. **Section image upload** via in-preview slots.  
3. Rich **save-status badge** machine.  
4. Monolithic content/design/publish shell + embedded project rename / status badge chrome.

These are **unreachable in production today** (only via orphan `ExperimentDetailPanel`). Live founders already live without them on B. Migrating them into B would be a **feature add**, not required for “delete A without regressing live Launch.”

### Unique-to-B (A lacks)

LaunchKit, share-copy variants, channel select, republish hooks in overlay, share tab structure, copy length caps on autosave, optimistic rollback.

---

## 5. Out-of-scope surfaces to preserve

| Surface | Exists? | Consumer today | Break if A deleted? |
|---------|---------|----------------|---------------------|
| `landing-templates/` | Yes | A preview + B `BrandMark`/`EditableCopy`/`SurfaceShell`; public via published | **No** if B imports unchanged |
| `landing-runtime-v2/` | **Absent** | — | N/A |
| `published/` | Yes | `app/e/[slug]` | **No** |
| Device preview iframes | `app/preview/device` + A DevicePreview* | Only A | Route becomes **orphaned infra** if A DevicePreview deleted; B does not use it |
| PDF export CSS | No Launch PDF stack; print styles live under Evidence (`validation-report-html-styles`) | Not Launch | **No** |

---

## 6. Shared subcomponents (both import graphs)

Do **not** need to move with A→B; only consumers change:

- `landing-templates/BrandMark`, `SurfaceShell.mergeSurfacePatch`, `EditableCopy` (B via BrutalistEditableField), `TemplateRenderer` / `PreviewErrorBoundary` (A preview only today)
- `distribution/ShareLinksPanel`
- `ui/ToastProvider`
- Libs: `lib/api` (`patchLandingPage`, `uploadProjectLogo`, `publishProject`), `lib/landing-page-data`, `lib/landing-flow`, `lib/landing-regen`, `lib/templates`, `lib/color-palettes`, `lib/branding`, `lib/surface`, `lib/landing-host`

**Exception — must relocate out of A before delete:** `LandingPageSlugEditor` (still physically under A, fv-* styled, imported by B).

---

## 7. Deferred items

| Item | Location | PR-4 effect |
|------|----------|-------------|
| `FloatingLaunchAskBar` | **Not in repo** | No touch |
| `listPublications` | `lib/api.ts` only (zero callers) | Untouched; stays dead helper |
| `cta_mode` backend read-side | Publish hardcodes waitlist; published page reads mode | Untouched; not unblocked |
| `fv-*` in `landing-page-editor/` | Whole A tree | **Deleted for free** except must **restyle or leave fv** on relocated SlugEditor |
| Live Watch card | `signal/SignalWatchingPanel*` (not Launch) | Untouched; remains deferred outside PR-4 |

---

## 8. Hardcoded color hazards on survivor (`launch/`)

Grep for `rgba(`, `#000`, `#fff`, `text-white`, `text-black`, `bg-white`, `bg-black`, `text-red-*`, `text-blue-*`, `text-purple-*`, `text-green-*`, `text-yellow-*`:

| File | Line | Styles |
|------|------|--------|
| `LivePagePreviewPanel.tsx` | 67–69 | Traffic-light dots: `border-black` + `bg-red-400` / `bg-yellow-400` / `bg-green-400` |

No other matches under `launch/`. (Pay-as-you-go dark-mode debt: those three spans.)

---

## 9. Test surface

| Test | Relation |
|------|----------|
| `lib/__tests__/launch-channel-intents.test.ts` | Channel intent **lib** — keep; not System A |
| `*.test.*` / `*.spec.*` under `landing-page-editor/` or `launch/` components | **None** |

No tests encode A autosave debounce or A upload flow. Deleting A does not orphan component tests. Relocating SlugEditor needs no test move today.

---

## 10. Size sanity check

| Bucket | Estimate |
|--------|----------|
| Delete System A tree | ~−4520 LOC |
| Must relocate `LandingPageSlugEditor` → e.g. `launch/` or `components/landing/` | ~+289 move + import path edits (~4 files) |
| Replace redirect `EditorLoadingSkeleton` with brutalist/simple skeleton | ~−31 + small add |
| Delete orphans `ExperimentDetailPanel` + `TemplatePicker` (compile deps of A) | Extra delete (detail panel is large; not counted in A sum) |
| Migrate unique A draft-preview / section images into B | **Optional / product**; hundreds–1k+ LOC if pursued — **not required** for live-path parity |

**Section 4 verdict:** Live Launch already is B. Unique A behaviors are **dead-path only**. PR-4 shape = **delete + relocate SlugEditor + fix redirect skeleton + delete A-dependent orphans**, not “migrate full EditorLayout into Launch.”

**Net change:** well **under 1500 LOC** of constructive edits; large deletion. **Single PR** is appropriate. Split only if product insists on porting draft DevicePreview into B in the same change set.

---

## 11. Baseline

```
a076af9 Loading flash fix: unify auth, add loading.tsx per route, three-state auth machine
92bfdf2 Part2 PR-2a: delete Evidence report-side orphans
8d2c56a Part2 PR-1: delete orphaned Insight, extract PanelHeader, audit Signal to brutalist north star
```

`npx tsc --noEmit`: **clean** (`TSC_EXIT:0`).
