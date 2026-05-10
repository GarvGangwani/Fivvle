# ADR 0007: No Payments in MVP — Free for Everyone During Launch Phase

**Status:** Accepted
**Date:** 2026-05

## Context

The original product plan included a freemium SaaS model:
- Free tier: limited usage, capped credits
- Paid tier: unlimited research runs, premium features
- Razorpay as the payment processor (India-first)

We need to decide whether to build payment infrastructure for the MVP launch.

Constraints:
- 4-month MVP timeline
- Pre-revenue, pre-funding
- Initial launch is to friends-and-circle (~10-20 users) for product feedback
- Early users won't pay regardless — they're providing learning, not revenue
- Per-experiment cost target is $1.50; absorbing this for early users is feasible

## Decision

**No payment processing in MVP.** Fivvle is free for everyone during the launch phase. Razorpay integration, subscription management, plan enforcement, and billing infrastructure are deferred to post-launch.

The MVP includes cost tracking infrastructure (LLMCall and ExternalAPICall tables) so we know exactly what we're spending per user, but we do not gate access based on payment.

Soft usage limits remain in code (5 refinement regenerations per experiment, 5 landing page field regenerations per page, 1-2 reflection loops per research engine run) — these prevent abuse but are not paywall mechanics.

## Reasoning

**Building payments before users is premature optimization:**
- Razorpay integration, webhook handling, subscription lifecycle, plan enforcement, and the admin tooling to support all of it is roughly 1-2 weeks of work
- That's 5-10% of our MVP timeline spent on infrastructure for users who don't exist yet
- Time spent on payments is time NOT spent on the research engine, landing pages, and other things that determine whether the product is good

**Early users are for learning, not revenue:**
- The friends-and-circle launch is about understanding what founders find valuable, what's confusing, what's missing
- Charging these users would add friction that gets in the way of feedback
- These users are providing us with insight; we're providing them with a product. That's the trade

**Cost economics work fine without payments early:**
- Per-experiment cost target: ~$1.50
- 100 experiments across the launch phase: ~$150 total cost
- This is well within tolerable absorption for a pre-revenue startup
- We will know exactly what we're absorbing because cost tracking is in from day one

**Building the paywall when we know what to charge for is better than guessing:**
- We don't yet know which features are most valuable
- We don't yet know what price founders are willing to pay
- We don't yet know whether paywall should be at "1 research per user lifetime" or "1 per month" or "first 3 free"
- Launching free, watching usage data, and then designing the paywall is dramatically more informed than guessing now

## Consequences

**What becomes easier:**
- MVP timeline shrinks by 1-2 weeks
- Onboarding has zero friction during the learning phase
- Early users have full access to the product, generating richer feedback
- We can change our mind about pricing model based on real data

**What becomes harder:**
- We are on the hook for all costs during the launch phase
- We need to monitor cost-per-user closely so we can identify when paywall becomes urgent
- We need to communicate to early users that pricing will eventually arrive (and that they may get grandfathered or discounted)

**What we accept:**
- We will absorb infrastructure costs during the friends-and-circle phase
- We will build payment infrastructure when one of these is true:
  - User count crosses ~200-300 (cost trajectory becomes meaningful)
  - We have product-market-fit signal strong enough to know what to charge for
  - Costs in any 30-day window approach a threshold we set in advance
- We will not let scope creep around payments during MVP — if "but what about subscriptions" comes up, the answer is "v2"

## Related

- ARCHITECTURE.md (Cost Tracking Architecture)
- ADR 0006 (Video Posting Deferred — same scope-cutting principle)
