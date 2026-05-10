# ADR 0006: Video Posting and Comment Harvesting Deferred to v2

**Status:** Accepted
**Date:** 2026-05

## Context

Original product scope included a video distribution flywheel: founders record a 30-60 second pitch video, the platform auto-posts to both the founder's Instagram/YouTube accounts AND Fivvle's brand accounts, then harvests comments across all four posts and runs AI sentiment/objection/demand-signal analysis to produce a behavioral validation report.

This was the centerpiece of the longer-term product vision. It directly addressed the "validate with strangers, not friends" thesis by exposing ideas to Fivvle's audience and capturing real reactions.

Several factors changed the scope conversation:
- TikTok was already out due to India ban
- Reddit's commercial API tier costs ~$12k/year, ruling it out for MVP
- Instagram Graph API requires Meta App Review (weeks of opaque process)
- YouTube Data API requires Compliance Audit for quota increases
- Most importantly: Fivvle has no existing brand audience. Founders' own accounts have small followings. Posting to small audiences yields no real strangers to gather reactions from.

The marketing/design lead made the case that automated posting is theater rather than validation when the brand audience doesn't exist yet.

## Decision

We will **defer video posting and comment harvesting to v2** of the product. The MVP ships with cognitive validation (refinement + research engine + validation report) and lightweight behavioral validation (founder-driven traffic to a hosted, tracked landing page with waitlist conversion).

Specifically out of scope for MVP:
- Multi-platform video posting (Instagram, YouTube)
- Comment harvesting from any platform
- AI comment analysis (sentiment, objections, demand signals)
- Pitch video upload and storage
- Social account OAuth for the founder
- Fivvle brand account posting infrastructure

These return when:
- Fivvle's brand audience is large enough that posting to it provides meaningful real-stranger feedback
- Meta App Review for Instagram production posting is approved
- The team has cycles to engineer the multi-platform integration properly

## Reasoning

**Posting to a non-existent audience is theater, not validation:**
The product's promise is real strangers reacting to a founder's idea. If the founder posts to their 50 followers and Fivvle's brand account has 200 followers, the resulting comments aren't strangers — they're warm-network noise dressed up as validation. The marketing lead correctly argued this would mislead founders rather than help them.

**The audience-building problem is its own startup-sized effort:**
Building a brand audience meaningful enough to provide real comment volume takes months of dedicated content production. Doing this in parallel with shipping the MVP would require either delaying the MVP or under-investing in audience-building. Neither is acceptable.

**The technical work was the largest in MVP scope:**
Multi-platform posting + comment harvesting + comment analysis would be roughly 6-8 weeks of focused engineering: Meta App Review, YouTube quota approvals, OAuth flows for founder accounts, brand account credential management, dual-account posting logic, comment polling cron jobs, dedup logic, batch LLM analysis, and synthesis into reports. Cutting it dramatically reduces MVP scope.

**Landing pages alone provide a meaningful (though weaker) behavioral signal:**
Page views with source-tag attribution + waitlist conversion + time-on-page captures real founder-driven traffic with reasonable signal-to-noise. Founders distribute the link themselves; warm-network bias is visible in the source tag breakdown; the AI insight report can call it out honestly.

**The team agreed:**
This wasn't a unilateral decision. The marketing lead surfaced the audience-existence problem; the engineering team agreed the timeline was tighter than originally hoped; the team aligned that landing-page-only validation is a defensible MVP that earns the right to build the video flywheel later.

## Consequences

**What becomes easier:**
- MVP timeline shrinks meaningfully (multiple weeks of work removed)
- No Meta App Review or YouTube quota timeline to coordinate
- No brand account infrastructure to manage
- No cross-platform comment harvesting/dedup logic to maintain
- Marketing lead can focus on building Fivvle's audience properly (when not building templates) instead of hacking together a half-working video flywheel

**What becomes harder:**
- The MVP is less differentiated from competing tools — "AI validates your idea + tracked landing page" is closer to existing products than the full vision
- Behavioral validation is weaker without comment data
- The compelling pitch deck narrative ("60 minutes from idea to real-world feedback") doesn't fully apply to MVP
- We need to communicate to founders that this is v1 and the video features are coming

**What we accept:**
- MVP differentiation comes from the quality of the cognitive validation (research engine) plus the polish of the landing pages, not from the video flywheel
- We will revisit this scope decision once Fivvle has 1,000+ followers/subscribers across the relevant social platforms (whichever audience-building strategy the marketing lead pursues)
- The architecture is built so that adding video posting + comment harvesting later doesn't require rewriting the existing system

## Related

- ARCHITECTURE.md (MVP Scope section)
- ADR 0007 (No Payments in MVP)
