# Security notes — accepted residual vulnerabilities

This file tracks vulnerabilities surfaced by dependency auditors (`npm audit`,
`uv pip audit`, GitHub Dependabot, etc.) that have been reviewed and consciously
accepted as not exploitable in Fivvle's context. Every entry includes the
GHSA/CVE identifier, affected package, why it was accepted, and the date of
review.

## Triage process

When a new audit flags something:

1. **Identify the attack path** — what conditions must hold for an attacker
   to exploit this?
2. **Check whether the path exists in Fivvle's codebase** — do we have the
   feature, input, or configuration the vulnerability requires?
3. **If yes** → fix it (upgrade, patch, or work around). Do not add to this file.
4. **If no** → document it here with the reasoning, and move on.

Review this file quarterly. Remove entries when the upstream is fixed, when
Fivvle's code paths change, or when a re-audit no longer surfaces the issue.

This file is not an excuse to ignore vulnerabilities. Every entry must include
a specific, verifiable reason the attack path does not exist in Fivvle. "Low
severity" or "probably fine" is not a reason.

## Frontend (npm)

### GHSA-qx2v-qp2m-jg93 — postcss XSS via Unescaped `</style>` in CSS Stringify Output

- **Package:** postcss, nested inside `node_modules/next/node_modules/postcss`
- **Severity:** Moderate
- **First flagged:** 2026-05
- **Status:** Accepted — not exploitable in Fivvle's context
- **Next review:** 2026-08

**Attack path:** Requires postcss to stringify CSS that contains attacker-controlled
content, where the malicious payload includes an unescaped `</style>` sequence that
breaks out of a `<style>` element when rendered.

**Why not exploitable in Fivvle:**

- Fivvle does not accept user-supplied CSS. Landing page customization is bounded
  to dropdowns and pre-defined template parameters (ADR 0005: designer-built
  templates over AI-generated landing pages).
- Tailwind generates CSS from class names in Fivvle's own code, not from user input.
- Next.js's bundled postcss is used at build time to process CSS that Fivvle wrote,
  not CSS that attackers send at runtime.
- AGENTS.md "Frontend-specific security" already forbids `dangerouslySetInnerHTML`
  with user-supplied content.

**Resolution path:** Will be resolved when Vercel publishes a Next.js 15.x patch
that bumps the bundled postcss to >= 8.5.10. Until then, the only "fix" npm audit
proposes is downgrading Next.js to 9.3.3, which is not a valid option.

**npm audit double-counts this issue** — it appears once for postcss directly and
once for "next depends on vulnerable postcss." Both refer to the same nested
postcss copy and the same CVE.

**Verification checks for future contributors:**

- Confirm no `dangerouslySetInnerHTML` is used with CSS content anywhere in the
  codebase.
- Confirm no user input flows into a CSS-in-JS library or inline `<style>` tag.
- Confirm landing page templates do not accept free-form CSS (per ADR 0005).

## Backend (pip)

(None currently. When `uv pip audit` flags something we accept, add entries here.)
