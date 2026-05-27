# Google Trends — Data Source Decision

**Status:** Reference — decision input, not a build commitment.
**Date:** 2026-05
**Audience:** Co-founders (product + budget call).
**Related:** ADR 0015 (Multi-Source Search Inputs, Proposed), ADR 0016 (Synthesizer 5-Field Contract, Proposed), `docs/planning/multi-source-searcher.md` §7, `docs/planning/master-index-gap-map.md` (§5 demand signals), `.cursorrules` Reliability ("Trends flaky: retry 3x then continue without; note in report").

---

## TL;DR

Google Trends (via pytrends) is the engine's only genuinely-sourced quantitative signal and feeds §5's demand chart — the most defensible chart in the eventual product. It has **never returned data in a real pipeline run** (M-1, M-2 both failed). Investigation this session found the integration code is **already correct**; the failure is **environmental** (Google throttling datacenter IPs), which is not fixable in code and offers no SLA.

**Decision:** three-stage path —
1. **Now:** keep best-effort pytrends, but it is **never load-bearing** for §5's chart.
2. **Bridge:** evaluate a reliable low-cost API (Trends MCP free tier) before spending money.
3. **Later:** move to a paid demand-data API when paying users justify the cost. **Trigger is left open** (see below).

---

## What the investigation found

A read-only diagnostic drove pytrends directly (no pipeline cost, no DB writes) and established:

1. **The Searcher is already correctly designed.** It builds one deduped ≤5-keyword bag and makes **one batched Trends call per run** — not the multiple calls the original plan sketched. There is no call-count bug to fix.

2. **pytrends can return data.** A single-keyword call returned a full 12-month series (53 weekly points). A 5-keyword batched call also returned all five series. So the integration and schema mapping work.

3. **The failure is rate-window throttling (HTTP 429).** A second live request fired seconds after the first got a 429; calls spaced further apart succeeded. The failure depends on request *timing* and *IP reputation*, not keyword count or code correctness.

4. **The diagnostic ran from a residential dev IP and mostly succeeded; M-1/M-2 ran from production-class infrastructure and failed.** Google throttles datacenter/cloud IPs far more aggressively than residential ones. This asymmetry is the most likely reason the two prior real runs failed while the laptop test passed — and it is **the environment paying users' reports actually run in.**

**Conclusion:** one successful dev-IP run is N=1 and does not generalize to production. pytrends scrapes an undocumented Google endpoint with no SLA; a single Google policy change can take §5's headline chart dark for every paying user at once. That is not a foundation a paid product's most defensible chart can rest on.

---

## Why this matters for the product (user value)

Founders convert to paid because the report tells them something true and useful. A demand chart that is reliably present and accurate builds trust. A demand chart that is **absent half the time, or silently stale, actively destroys trust** — a founder making a go/no-go decision on missing or bad demand data is the exact failure mode Fivvle exists to prevent. An unreliable Trends source is therefore not neutral; it is a liability dressed as a feature.

---

## The path

| Stage | What | Cost | Reliability |
|-------|------|------|-------------|
| **Now** | Keep best-effort pytrends. Graceful-skip on failure (already built). Never the sole basis of §5's chart; §5 must degrade honestly when Trends is absent. | $0 | Low — works sometimes, not in production reliably. |
| **Bridge** | Evaluate **Trends MCP** free tier (~100 requests/day, likely covers MVP volume) as a more reliable drop-in. | $0 at MVP volume | Medium — unverified; needs an evaluation run. |
| **Later** | Paid demand-data API (e.g. Glimpse) once paying users fund it. Official Google Trends API is ~1 year out. | Glimpse ~$49/mo floor; **real API access is enterprise / contact-sales, likely $500+/mo**. | High — SLA-backed. |

### Cost reality (pre-revenue)

$500+/month for one chart is hard to justify before revenue. The bridge stage exists precisely so we are not forced to choose between "unreliable free" and "expensive paid" today.

### Important caveat on the bridge

Trends MCP is an **MCP server**, not a Python library. The stack calls integrations as direct Python wrappers in `backend/app/integrations/` (`.cursorrules`: research engine is plain asyncio, not MCP-wired). Adopting it means either calling its underlying HTTP API from a new wrapper or confirming a plain REST endpoint exists. Either way it is a **new external API integration**, which per `.cursorrules` requires a **new ADR (next free: 0017)**. It is not a config swap.

---

## Open trigger (decide later)

**What flips the switch from best-effort/bridge to a paid API is intentionally left open.** Candidate triggers to decide when there's more signal:
- Product-gated: before §5's demand chart is exposed to *paying* users.
- Revenue-gated: at first meaningful MRR.

This memo does not pick one. It logs the trigger as an explicit open decision so it is not forgotten.

---

## What does NOT change

- `backend/app/integrations/trends.py` — correct as-is; no fix.
- `backend/app/services/searcher_service.py` — already single-batched; no fix.
- ADRs 0015 / 0016 stay **Proposed**. They were gated on Trends returning data in a real run; given the environmental failure, **promotion should not be gated on pytrends specifically** — revisit promotion criteria once a reliable source (bridge or paid) is in place.

## Logged follow-ups (cheap, non-blocking)

- Optional dev diagnostic: confirm whether `retry_async` retries *into* the throttle window (refines best-effort behavior; does not change direction).
- §5 must carry an honest "demand data unavailable" state when Trends is absent (ties to the still-open Synthesizer trends-disclosure compliance bug).
