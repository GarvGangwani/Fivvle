# Signal act

Design contract for the fifth and final act of the experiment canvas. Not an ADR.

## 1. Purpose

Signal is the closing act: meter behavioral evidence from the live landing page, then surface a verdict. The founder opens Signal to answer one question — whether there is enough real-world signal to generate (or review) an Insight report — and then to act on that report.

Signal is not Launch (page editing and distribution stay in Copy / Design / Share / Kit). It is not a community-observation surface (Reddit Voices stay inside Evidence). It is not a sixth act and not a separate “Metrics” act — metrics *are* Signal’s Watching state.

## 2. Three states

Internal state is driven by `experiment.status` plus (from PR 2) a server-side threshold flag. The client never computes the min-data threshold itself.

### Idle

**Trigger:** status is anything before a live landing page — not `LANDING_LIVE`, and not yet in the insight lifecycle (`INSIGHT_*` / `COMPLETED`).

**Founder sees:** a short message — “Signal opens once your landing page is live.” No charts, no unlock CTAs.

**Actions:** none in Signal. Path forward is publish from Launch.

### Watching

**Trigger:** status is `LANDING_LIVE` and the server says the min-data threshold is **not** met.

**Founder sees:** a hero that communicates **distance to threshold** (how far from “enough signal”), not raw view/signup numbers as the hero. Supporting detail (counts, sources, etc.) can sit below once data plumbing lands (PR 3). This is the Metrics surface, re-homed here.

**Actions:** Watching renders a single secondary action: a link back to the Launch act's Kit tab ("Get more traffic → Launch / Kit"). Share links, trackable URLs, and post-to-channel actions are not duplicated in Signal. No Insight generate until threshold is met.

### Verdict

**Trigger:** server says threshold **is** met, **or** status ∈ {`INSIGHT_GENERATING`, `INSIGHT_READY`, `INSIGHT_FAILED`, `COMPLETED`} (insight lifecycle already started or finished).

Verdict is not one screen. Substates:

1. **Eligible** — threshold met, status still `LANDING_LIVE`, no insight generated yet. Founder sees: the meter reading “threshold crossed” plus a primary Generate Insight CTA. Actions: generate (`insightReport` credit-gated).
2. **Generating** — status `INSIGHT_GENERATING`. Progress state with polling. Actions: none.
3. **Ready** — status `INSIGHT_READY` or `COMPLETED`. Insight report, regenerate, and founder decision (`proceed` / `iterate` / `pivot` / `kill`). Recording a decision **persists without archiving** — the project stays open and readable. Archiving remains a separate, voluntary filing action.
4. **Failed** — status `INSIGHT_FAILED`. Error state. Actions: retry (credit behavior follows the existing refund path — do not restate it here).

**Paywalls (two products, do not conflate):**

- **`metricsAnalysis` (20 credits)** — formerly gated `GET /experiments/{id}/analytics`. **The gate is removed outright in PR 2** — not auto-purchased. Access is now a landing-page-is-live-and-unarchived check, with no wallet involvement and no phantom purchase written to any founder's ledger. The `SERVICE_PRICING` key, `/unlock-metrics`, and `/metrics-access` survive as deprecated no-ops until PR 6. `MetricsAnalysisPrompt`, `MetricsPaywallModal`, and `useMetricsPaywallGate` become dead code.
- **`insightReport`** — gates Insight generation. **This gate stays.** Verdict surfaces it: insufficient credits use the existing wallet paywall flow, not a metrics unlock.

Rationale: metering a founder’s own published page is free; synthesis is the paid product.

### Archived experiments

Signal derives its shell from *data*, not status, when archived: a landing page with `live_at` set implies the Watching shell; an existing `InsightReport` row implies the Verdict shell. Both render read-only — no Generate Insight, no retry, no decision recording. `_ensure_metrics_access_allowed` rejects archived analytics access server-side; the client must not present actions the server will refuse. Data-driven derivation lands with PR 3 (Watching) and PR 4 (Verdict); PR 1 ships a status-only Idle placeholder as a known interim.

## 3. The one decision Signal helps the founder make

**“Do I have enough signal to draw a verdict?”**

The ratchet is the existing min-data threshold (server-authoritative):

- ≥10 page views, **or**
- ≥1 waitlist signup, **or**
- ≥7 days live

Meeting any one flips Watching → Verdict eligibility. Below threshold, Signal’s job is to make the gap visible (distance-to-threshold), not to invent a second metrics act.

Watching never asks for `metricsAnalysis` credits. Verdict may ask for `insightReport` credits when generating.

### Threshold contract (client consumes; server computes)

PR 3 designs against this shape; PR 2 implements and settles final field names:

```
insight_threshold_met: bool
insight_progress: {
  views_current: int, views_target: int,
  signups_current: int, signups_target: int,
  days_current: int, days_target: int,
}
```

The client renders progress from these fields and performs **no** threshold arithmetic. The existing `meetsInsightThreshold` helper in `MetricsWidget.tsx` — which omits the `days_live >= 7` arm and can block a founder the backend would allow — is deleted in PR 2.

## 4. What replaces what

| Old | New |
|---|---|
| `MetricsStagePanel`, `MetricsWidget` | `SignalStagePanel` Watching state |
| `InsightStagePanel`, `InsightReportViewer` (orphaned off retired detail panel) | `SignalStagePanel` Verdict state (re-home, not rewrite) |
| `DecisionPanel` | `SignalFounderDecisionPanel` — persists via `PUT /founder-decision`; does not archive |
| `ExperimentDetailPanel` (retired) | n/a — canvas already replaced it |
| `MetricsAnalysisPrompt`, `useMetricsPaywallGate`, `lib/metrics-flow.ts` | none — deleted; metrics paywall removed in PR 2 |
| `DistributeSection` (share + mini metrics hybrid) | split: share behavior already lives in Launch Kit `ShareLinksPanel`; mini-metrics behavior absorbed into Signal Watching |
| `lib/experiment-stages.ts` `metrics` / `insight` stage ids | none — dead after PR 6 |

## 5. PR sequence

1. **PR 1** — Planning doc + Signal shell scaffolding in DeepDive (placeholders only).
2. **PR 2** — Remove `metricsAnalysis` gate (free live analytics); server-side threshold flag; remove client-side threshold math.
3. **PR 3** — Watching state data plumbing (analytics, distance-to-threshold hero).
4. **PR 4** — Verdict state: sticky shell + status poll, ported report viewer, Eligible / Generating / Ready / Failed (no decision UI).
5. **PR 5** — Verdict persistence + decision recording: migrate so founder outcome (`iterate` / `proceed` / `pivot` / `kill`) is stored; then re-home decision UI. Today `/archive` discards `ArchiveRequest.outcome` and only archives.
6. **PR 6** — Delete orphaned Metrics/Insight stage wiring; retire dead `metrics` stage id / deep links as needed.

## 6. Non-goals for this act

- No Watch / metrics card or tab inside Launch Kit (Launch stays Copy / Design / Share / Kit).
- No conversion rate on dashboard project cards.
- No community-observation / Voices surface under Signal.
- No rescue of `?stage=metrics` / `?stage=insight` deep links in this act’s core work (deferred cleanup).

## 7. Open items deferred to later PRs

- Canvas Launch node `landing_page_view_count` vs unlocked analytics / card stats — drift review.
- Dashboard `card_stats` reconciliation with Signal / analytics.
- URL migration for `stage=metrics` / `stage=insight`.
- DeepDive status/slug lift — done in PR 3.
- Amending a founder decision **overwrites** the prior value — no history trail.
- Insight-report version pinning for decisions deferred (`InsightReport` is 1:1 and mutable on regenerate).
- `ArchiveRequest.outcome` still accepted by `/archive` but never written — deprecate in PR 5 Group 3.
