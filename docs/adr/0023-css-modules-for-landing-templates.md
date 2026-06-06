# ADR 0023 — CSS Modules Permitted for Landing Page Templates

**Status:** Proposed  
**Date:** 2026-06  
**Supersedes:** none (upon acceptance, narrows the Tailwind-only rule in `.cursorrules` Template Stack and `ARCHITECTURE.md` § Stack for templates)  
**Related:** ADR 0005 (designer-built templates), ADR 0022 (landing page generator pipeline)

## Context

Fivvle's frontend styling convention, documented in `.cursorrules` Template Stack and `ARCHITECTURE.md` § Stack for templates, requires:

> Tailwind CSS only — no styled-components, no CSS modules, no plain CSS files

That rule was written when the project had no landing page templates — only the app shell (dashboard, auth, editor, navigation, forms). The intent was UI consistency across internal product surfaces: one utility-first system, no parallel styling paradigms, no global CSS leakage, predictable patterns for coding agents and backend-focused contributors.

The design co-founder has since delivered **6 designer-built landing page templates** as self-contained React components. The reference implementation lives under `reference/frontend-src/components/landing-page-generator/templates/` and uses **CSS modules** — one `.module.css` file per template plus a shared `template-base.module.css` for cross-template primitives (section spacing, typography rhythm, responsive breakpoints). Each template includes complex presentation concerns that are awkward or fragile in pure Tailwind:

- Multi-stop gradients and background meshes
- Keyframe animations and staggered entrance effects
- Template-specific grid/flex layouts with many breakpoint overrides
- Scoped pseudo-elements and nested selectors for editorial typography

These templates are the **primary user-facing product surface** for behavioral validation — the page founders publish and share. ADR 0005 committed to designer-built, parameterized templates rather than AI-generated layouts. ADR 0022 defines how the backend populates those templates with copy and theme config. The styling layer is part of the designer's deliverable, not an app-shell concern.

Converting all six templates from CSS modules to Tailwind-only would:

- Risk degrading design fidelity (gradients, animations, spacing nuance)
- Require weeks of rewrite work with no user-facing benefit
- Force the design co-founder to maintain templates in a stack they did not author
- Produce enormous Tailwind class strings that are harder to read and diff than scoped module rules

CSS modules provide **style isolation between templates** — class names are hashed at build time, so `dark-premium`'s `.hero` cannot collide with `bold-v1`'s `.hero`. This matters when six visually distinct templates coexist in one codebase and are swapped at runtime via `template_id`.

## Decision

**CSS modules (`.module.css` files) are permitted exclusively inside the landing template directory:**

```
frontend/components/landing-templates/
```

(or an equivalent path reserved solely for public landing page template components — not editor chrome, not dashboard, not preview wrappers unless those wrappers are Tailwind-only).

### Permitted within `landing-templates/`

- One `.tsx` component file per template (e.g. `DarkPremiumTemplate.tsx`)
- One `.module.css` file per template (e.g. `dark-premium.module.css`)
- One shared `template-base.module.css` for primitives reused across templates (section wrappers, prose defaults, responsive containers)
- `types.ts` and `index.ts` barrel exports (no CSS)

**File contract per template:** exactly **1 `.tsx` + 1 `.module.css`**, plus the shared base module. No additional plain `.css` files, no styled-components, no CSS-in-JS.

Templates may still use Tailwind utilities for simple, one-off adjustments (e.g. `className="sr-only"`) where appropriate, but the primary styling surface is the module file.

### Not permitted (unchanged)

CSS modules, plain CSS files, and styled-components remain **banned** everywhere else in `frontend/`:

- Dashboard, experiment list, insight views
- Auth flows, onboarding, settings
- Landing page **editor** UI (template picker, copy editor, preview chrome)
- Navigation, forms, modals, toasts
- `app/` layout shells outside the public `/e/[slug]` render path

All non-template UI stays **Tailwind-only**, consistent with the original rule's purpose.

### Documentation update on acceptance

When this ADR is accepted, a human updates:

- `.cursorrules` § Template Stack — add explicit exception for `frontend/components/landing-templates/**/*.module.css`
- `ARCHITECTURE.md` § Stack for templates — same boundary language
- ADR 0005 Related note (optional) — templates may use CSS modules despite the original "Tailwind CSS" wording

This ADR does **not** modify those files while status remains Proposed.

## Reasoning

### Why templates are a special case

**Design-heavy, not utility-heavy.** App UI optimizes for consistency and speed of iteration — buttons, forms, and tables share a design language. Landing templates optimize for conversion aesthetics — each template is a distinct brand experience (dark premium vs bold consumer vs editorial narrative). That diversity maps naturally to scoped stylesheets authored by a designer, not to a shared Tailwind token system.

**Self-contained presentation components.** Each template is a leaf component: it receives `LandingPageProps` (or the extended `page_json` contract from ADR 0022), renders public HTML, and does not compose with app-shell components. There is no cross-import styling dependency with the dashboard. Isolating templates in their own directory with their own styling mechanism does not fragment the app UI system.

**Maintained by the design co-founder.** Templates are authored and iterated by the person responsible for visual quality. Requiring a Tailwind-only rewrite forces a translation layer between design intent and implementation, increases merge friction, and makes the design co-founder dependent on Tailwind expertise for changes that are already correct in CSS modules.

**User-facing product surface.** A founder's published page at `fivvle.io/e/{slug}` is what prospects see. Degrading template fidelity to satisfy an app-shell styling rule would undermine ADR 0005's goal: pages good enough that founders publish them instead of rebuilding on Carrd or Framer.

**Style isolation at scale.** Six templates with overlapping section names (`hero`, `features`, `cta`) in one repo benefit from CSS modules' automatic scoping. A single global Tailwind config cannot capture per-template animation keyframes and gradient definitions without polluting the shared theme or producing unmaintainable arbitrary-value classes.

### Why Tailwind-only remains correct for everything else

**Single paradigm for product engineering.** Dashboard, editor, and auth are built by engineers optimizing for consistency, accessibility patterns, and rapid feature work. Tailwind's utility model keeps those surfaces uniform and lets coding agents apply predictable class patterns without reading separate stylesheets.

**No precedent for CSS modules elsewhere.** Allowing modules in one place with a hard directory boundary is easier to enforce in code review than allowing modules "where needed." The rule is binary: `landing-templates/` yes, everything else no.

**Editor and preview chrome stay simple.** The in-app landing page editor (template swap, inline copy edit, regenerate buttons) is app UI. It should not inherit template CSS or require module imports. Preview iframes or isolated renders load template components; the surrounding editor UI remains Tailwind.

**Build and bundle impact is bounded.** Next.js supports CSS modules natively. Six module files plus one base file add negligible bundle overhead compared to the alternative (thousands of Tailwind arbitrary values duplicated across templates).

## Consequences

**What becomes easier:**

- **Ship designer deliverables as-is.** Reference templates (`dark-premium`, `bold-v1`, `minimal-v3`, `editorial-saas`, `aether`, `abstract`) port into `frontend/components/landing-templates/` without a styling rewrite.
- **Preserve design fidelity.** Gradients, animations, and layout nuance stay under the designer's direct control.
- **Clear enforcement boundary.** Code review and lint rules can scope-check: `.module.css` only under `landing-templates/`.
- **Template independence.** Each template's styles are encapsulated; adding a seventh template does not risk breaking existing ones.

**What becomes harder:**

- **Two styling systems in one frontend.** Engineers working on both dashboard and templates must context-switch between Tailwind utilities and CSS module class maps. Mitigation: templates are a read-mostly leaf directory after initial integration.
- **Documentation must stay explicit.** Agents and contributors need the directory boundary in `.cursorrules` to avoid proposing CSS modules for app UI. Acceptance updates are required.
- **ADR 0005 wording drift.** ADR 0005 states templates are "React Server Components in TypeScript with Tailwind CSS." Acceptance should add a footnote or amend that line to reference this ADR.

**What we accept:**

- Landing templates are the **only** exception to the Tailwind-only frontend rule for MVP and v1.
- `styled-components`, plain global `.css`, and CSS modules outside `landing-templates/` remain banned.
- Template-specific styles are not tokenized into the shared Tailwind theme — customization knobs (palette, fonts) are applied via props/CSS variables as defined in `template-base.module.css` and per-template modules, aligned with ADR 0022's `page_json` theme applicator.
- Future templates must follow the 1 `.tsx` + 1 `.module.css` + shared base contract; no ad-hoc styling escapes.

## Related

- **ADR 0005** — Designer-built parameterized templates; AI populates copy within fixed layouts, does not generate CSS
- **ADR 0022** — Landing page generator pipeline; backend emits `page_json` consumed by these template components
- `.cursorrules` § Landing Page Template Implementation, § Template Stack (to be updated on acceptance)
- `ARCHITECTURE.md` § Landing Page Architecture, § Stack for templates (to be updated on acceptance)
- `reference/frontend-src/components/landing-page-generator/templates/` — designer deliverable using CSS modules (`*.module.css`, `template-base.module.css`)
