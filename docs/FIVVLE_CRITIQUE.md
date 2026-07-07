# Fivvle — Critical Read

*Written 2026-07-05. Companion to `FIVVLE_PROJECT_SUMMARY.md`. Observations, not fixes — for your own thinking before deciding what to prioritize next.*

---

## 1. The "Business Construction Engine" oversells what it currently does

The name (and the new prompt block telling the Synthesizer to "communicate, not re-derive") implies genuine per-idea reasoning. In practice, today's implementation is:

- Hypotheses come from a **fixed dictionary of ~3 canned sentences per theme**.
- "Founder decisions" map to **one of 7 hardcoded action strings**, keyed only by theme.
- The "debate" that picks a winning hypothesis is just `supporting_count - contradicting_count` on evidence atoms.

This is honestly labeled "v1 deterministic" in its own code comments, and the team's own implementation doc flags LLM-backed reasoning as future work — so nobody's hiding this. But it means: right now, two very different startup ideas that both cluster into a "market" theme with similar evidence counts will get the **same templated hypothesis text**. If a founder-facing report implies "we reasoned about your specific business," and it's actually filling in a Mad Libs template, that's a gap worth closing before it's leaned on in marketing or sold as a differentiator.

**Worth deciding:** is this shipped as "v1, visibly labeled as directional" to users, or does it need to reach genuine per-idea reasoning before it's customer-facing?

## 2. Evidence clustering is keyword-matching, not understanding

Theme classification and contradiction detection both work off small hardcoded word lists (e.g. `{"grow", "growing", "demand"}` vs `{"decline", "fail", "churn"}`). This is brittle: any evidence that doesn't happen to use these exact words won't cluster correctly, and clusters can end up thin or empty for perfectly good ideas whose sources just phrase things differently. Since the Business Construction Engine above is built entirely on top of these clusters, weaknesses here propagate directly into the founder-facing report.

**Risk:** an idea could get told "insufficient evidence to reason about market fit" purely because of vocabulary mismatch, not because the research was actually thin.

## 3. Two landing-page generation systems, diverging philosophies, no reconciling decision yet

- **V1** (production) deliberately keeps page *layout* non-AI-generated — copy and template selection only. This was a considered decision (ADR 0005) specifically to bound cost and design risk.
- **V2** (in progress, isolated) has an LLM emit `design_tokens` and page `components` — this looks like it's generating actual page structure, which is the exact thing ADR 0005 decided against for V1.

There's no ADR for V2 yet, and it currently exists as "isolated, doesn't touch V1" — which is safe engineering, but it also means you now have two landing-page systems to maintain, and no stated decision about whether V2 is meant to **replace V1**, run as an **A/B experiment**, or become a **premium tier**. Left undecided, this tends to quietly become permanent duplicate surface area (two sets of prompts, two DB tables, two frontends to keep in sync).

**Worth deciding soon**, before more is built on top of V2: what is V2 *for*, specifically, and what's the plan to retire or merge with V1?

## 4. Payments shipped ahead of the architecture docs

`ARCHITECTURE.md` and `AGENTS.md` still describe payments as "deferred to v3 / free for everyone in MVP." A full Razorpay wallet + coupon + credit-ledger system already shipped in the most recent commit. This isn't a problem in itself — it just means:

- Those docs are now actively misleading about current scope.
- If you (or an AI assistant) make a decision based on "we said payments are deferred," that decision will be wrong.

This is a cheap fix (update two docs) but worth doing promptly, since stale architecture docs compound — the next feature built "because payments aren't live yet" would be a real mistake.

## 5. A safety-relevant question in the Reflector's error path, worth explicitly verifying

The Reflector pipeline has three exit paths (normal, disabled, exception-caught), and all three now call a new `_finalize_reflector_summary()`, which itself does real work (collecting evidence atoms, running analysis). The exception path exists specifically so that *if the Reflector itself fails, the pipeline degrades gracefully rather than crashing* — that's a documented guarantee. The open question: can `_finalize_reflector_summary()` itself throw an exception when called from inside that exception-handling path? If it can, the "Reflector never fails the pipeline" guarantee could be silently broken by the very code meant to preserve it. This is a five-minute check, not a redesign, but it's the kind of thing worth confirming rather than assuming.

## 6. `fivvle-local-secrets.zip` sits untracked at the repo root

It isn't staged for commit, and may already be `.gitignore`'d — but its presence in the repo root at all is worth a second look. A future `git add -A`, a zip/archive step, or an unrelated broad commit could pull it in. Given the project's own security rules explicitly call out secret-handling, this is worth either confirming the gitignore covers it, or just moving it outside the repo folder entirely.

## 7. Rapid redesign cycles on the report viewer suggest unresolved product uncertainty, not just polish

Four consecutive commits reworking `ReportCanvas` (independent scrolling → premium styling → minimal → "continuous document") in a short span reads less like normal iteration and more like the team not yet having a settled point of view on how the single most important artifact in the product — the Validation Report — should actually look and feel. That's not inherently bad (better to iterate than to commit to a stale design), but if this is still moving, it's worth asking whether the underlying uncertainty is really about *visual design*, or about *what information the report should foreground* — those are different problems with different fixes.

## 8. Known, acknowledged gap: Reddit integration is built but unused

`backend/app/integrations/reddit.py` (via PRAW) is fully implemented and even cost-tracked, but never called by the search phase. The team's own docs already flag this, so it's not a surprise — just noting it since Reddit is often a rich source for early-stage market signal (niche communities, complaints, unmet needs) and may be a higher-leverage addition to the Searcher phase than it might appear from the backlog alone.

---

## Bottom Line

The core research pipeline is the most mature, well-guardrailed part of the system, and the engineering discipline (ADRs, cost logging, backward-compatible schemas) is genuinely a strength — this isn't "vibes-coded." The two things most worth your attention right now are (1) making sure the Business Construction Engine's actual capability level (templated, not reasoning) is either upgraded or clearly represented to users before it's leaned on, and (2) making an explicit call on what Landing Page V2 is *for* before more gets built on top of it. Both are product decisions, not engineering ones — the code is ready to be pointed in either direction.
