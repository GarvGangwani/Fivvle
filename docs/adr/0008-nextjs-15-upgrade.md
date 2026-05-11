# ADR 0008: Upgrade Next.js 14 → 15 and React 18 → 19 to Address Unpatched RSC DoS Vulnerabilities

**Status:** Proposed
**Date:** 2026-05

## Context

ADR 0002 established Next.js 14 + React 18 as the frontend stack, with exact-pinned versions (Next 14.2.35, React 18.3.1, eslint-config-next 14.2.35). These pins were chosen for peer-dependency compatibility and to match Next 14's well-tested release line.

While scaffolding the frontend in May 2026, `npm audit` surfaced five vulnerabilities in the dependency tree. Three are high-severity issues in Next.js itself:

- GHSA-h25m-26qc-wcjf (CVE-2026-23864) — HTTP request deserialization DoS via RSC
- GHSA-q4gf-8mx6-v5v3 — Denial of Service with Server Components
- GHSA-9g9p-9gw9-jx7f — Image Optimizer DoS via remotePatterns
- GHSA-ggv3-7p47-pfv8 — HTTP request smuggling in rewrites
- GHSA-3x4c-7xq6-9pq8 — next/image disk cache exhaustion

Investigation of the published Vercel security advisory for the most severe of these (GHSA-h25m-26qc-wcjf) showed the fixed versions are: 15.0.8, 15.1.12, 15.2.9, 15.3.9, 15.4.11, 15.5.10, 15.6.0-canary.61, 16.0.11, 16.1.5. No Next 14.x patch is listed. Vercel has not backported the RSC DoS fix to the 14.x line and treats Next 14 as effectively EOL for new security backports.

Since Fivvle's frontend is the public-facing surface — including landing pages linked from social channels — running an unpatched DoS vulnerability is not acceptable, even for a friends-and-circle launch. A founder's landing page being crashed by a single crafted HTTP request would defeat the product's core promise of "hosted, tracked landing pages."

The frontend currently contains only scaffolding (empty directories, configs, no React components). This is the cheapest possible moment to perform a major-version upgrade — there is no code to migrate.

Three options were considered:

1. **Upgrade Next 14 → 15** (with corresponding React 18 → 19 jump)
2. **Accept the vulnerability for MVP, document it, fix before public launch**
3. **Upgrade Next 14 → 16**

## Decision

Upgrade the frontend stack to Next.js 15 + React 19. Exact pins:

- next: 15.5.10
- react: 19.0.0
- react-dom: 19.0.0
- @types/react: 19.0.0
- @types/react-dom: 19.0.0
- eslint-config-next: 15.5.10

All other frontend pins (TypeScript, Tailwind 3.4.19, autoprefixer, postcss, firebase, lucide-react, ESLint 8.57.1) remain unchanged. Tailwind stays on 3.x because we have not committed to v4's new engine.

Update `.cursorrules` Tech Stack section: "Next.js 14+ App Router" → "Next.js 15+ App Router with React 19".

## Reasoning

**Why not Option 2 (accept and defer):** The vulnerability requires no authentication and is exploitable over the network with low complexity (CVSS 7.5). Public landing pages are exposed to anyone with the URL. Even during the friends-and-circle phase, URLs will be shared on social channels and indexed by anyone with the link. Running known-unpatched RSC DoS in production is not a defensible position.

**Why not Option 3 (jump to Next 16):** Next 16 released only days before this decision, removes `next lint`, requires migration to flat ESLint config, and makes further breaking changes around async APIs (sitemap `id` becomes a Promise, scroll behavior changes, runtime config removed). For an MVP foundation, this is too much novelty in a dependency we will rely on heavily. Next 15 has 6+ months of stability and a well-documented upgrade path from 14.

**Why now is the cheapest moment:** The frontend has zero React components. The Next 15 breaking changes (async `cookies()`, `headers()`, `params`, `searchParams`) require no migration work because there is nothing to migrate. Upgrading before any components are written means we adopt the new APIs as the only APIs we ever use.

**Why React 19 follows automatically:** Next 15 requires React 19. They are co-released and not separately versionable. The React 18 → 19 changes (new `use()` hook, removed deprecated APIs, refined Suspense behavior) similarly require no migration because there is no code to migrate.

**Specific patch choice (15.5.10):** This is the latest released patch in the 15.x line that includes fixes for GHSA-h25m-26qc-wcjf and the other listed CVEs. Choosing 15.5.x over earlier 15.0.x–15.4.x patches gives us the largest set of backported fixes without leaving the 15 major.

## Consequences

**What becomes easier:**
- `npm audit` returns clean (or with only known dev-chain noise)
- Public landing pages are protected against the published RSC DoS attacks
- Adopting React 19 APIs (the `use()` hook, async dynamic APIs) from day one
- Future upgrades to Next 16 in v2 are smaller (1 major instead of 2)

**What becomes harder:**
- All future frontend code must use async `cookies()`, `headers()`, `params`, `searchParams` patterns (this is the new norm, not actually harder)
- React 19's stricter behavior around effects and rendering may surface bugs that React 18 hid (this is good, but means more careful reviewing)
- Third-party React libraries we may want to use must support React 19 — we accept that some libraries may lag, but our stack is intentionally minimal (no UI libraries except lucide-react, which supports React 19)

**What we accept:**
- The frontend co-founder (joining in two weeks) will learn Next 15 patterns, not Next 14 patterns. This is fine — Next 15 is the current LTS line.
- This is a major-version dependency change, which is exactly the kind of decision this ADR exists to record. Future contributors looking at the pins will understand why we are on Next 15 specifically.

## Related

- ADR 0002 (FastAPI + Python over Node.js — established the original Next.js 14 + React 18 pin; this ADR updates the frontend portion of that decision)
- AGENTS.md "Dependency management" — requires running `npm audit` and addressing vulnerabilities
- Vercel advisory GHSA-h25m-26qc-wcjf (CVE-2026-23864)
- Next.js 15 upgrade guide: https://nextjs.org/docs/app/guides/upgrading/version-15
