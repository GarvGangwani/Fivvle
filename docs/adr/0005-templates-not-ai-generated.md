# ADR 0005: Designer-Built Templates over AI-Generated Landing Pages

**Status:** Accepted
**Date:** 2026-05

## Context

Founders using Fivvle need landing pages they can publish to drive traffic to and collect waitlist signups. The product's behavioral validation depends on these landing pages being good enough that founders actually use them rather than rebuilding on Carrd, Framer, or Lovable.

Two architectural approaches were considered:

1. **AI-generated landing pages.** The system generates a fully custom React/HTML/CSS landing page per idea, like Lovable or v0. Fully novel layouts, novel CSS, novel component arrangements per founder.

2. **Designer-built parameterized templates.** A small set of templates is designed and coded by hand, each with bounded customization knobs (color palette, font pair, density, optional sections). AI selects which template fits the idea best, picks customization values, and fills in copy. AI does not generate layouts or CSS.

## Decision

We will use **5 designer-built parameterized templates** with bounded customization. AI's role is selection and copy population within templates, not layout generation.

Templates are:
- Minimal (B2B SaaS, productivity, dev tools)
- Bold/Vibrant (consumer, design-forward)
- Indie (solo founder projects, side projects)
- Dark/Premium (dev tools, AI products)
- Editorial (content-first, social impact)

Each template implements the same `LandingPageProps` interface, supports 5 color palettes, 3 font pairs, density toggle, and a defined set of optional sections.

Templates are designed and coded by the marketing/design lead as React Server Components in TypeScript with Tailwind CSS.

## Reasoning

**AI-generated layouts cost too much per page:**
A truly AI-generated landing page (layout + CSS + content) requires a research-engine-sized LLM call per page. At rough estimates, $1-3 per landing page. With 1000 founders, that's $1000-3000/month in landing page generation alone — meaningful for a pre-revenue startup. Templates are essentially free per page after the initial designer investment.

**AI-generated layouts have variable quality:**
The output of "generate a landing page for this idea" varies wildly across LLM calls. Sometimes great, sometimes broken layouts, sometimes weird CSS, sometimes accessibility issues. Founders who get the broken one will be unhappy and rebuild elsewhere. Designer-built templates have predictable quality every time.

**AI-generated layouts are hard to maintain:**
If we discover a bug across all landing pages, we can't fix it once and have it propagate. Each AI-generated page is bespoke. With templates, fixing a bug in the template fixes it for every page using that template, retroactively (via ISR cache invalidation).

**AI-generated layouts have accessibility risks:**
LLMs don't reliably produce semantic HTML, proper ARIA labels, keyboard navigation, or color contrast that meets WCAG. Manually-coded templates can be designed and tested for accessibility once and inherit those properties for every page.

**We cannot replicate Lovable's quality in our timeline:**
Lovable has invested years and significant engineering in their AI design system. Two developers in 4 months cannot build something competitive with that. Pretending otherwise leads to shipping something worse than what founders could build elsewhere.

**Designer-coded templates with bounded AI customization gives "feels generative" UX:**
The AI picks template, picks palette, picks font pair, toggles sections, fills copy. The customization UI lets founders swap any of those values. The experience feels personalized even though every choice is bounded. This is similar to how Notion and Linear give the impression of design flexibility within tightly-controlled design systems.

## Consequences

**What becomes easier:**
- Quality is predictable — every page looks professional
- Mobile-responsive design handled once per template, inherited by all pages
- Accessibility handled once per template
- Bug fixes propagate to all pages of that template
- ISR caching works straightforwardly (templates produce predictable output)
- Cost per landing page is essentially the AI selection call (~$0.05) plus optional regeneration calls (capped at 5 per page)

**What becomes harder:**
- We can't market "fully AI-generated landing pages" as a feature
- Founders who want highly-bespoke layouts have to look elsewhere (we accept this — Fivvle isn't a website builder)
- We're dependent on the quality of the 5 templates; if a founder doesn't like any of them, we have limited recourse

**What we accept:**
- Templates are a v1 deliverable that will be iterated post-launch based on founder feedback
- Adding a 6th, 7th, or 8th template is a future option
- Fully AI-generated layouts may be revisited in v2 if/when LLM design quality improves substantially or we have funding to invest in this specifically

## Related

- ARCHITECTURE.md (Landing Page Architecture)
- `.cursorrules` (Landing Page Template Implementation)
- LANDING_TEMPLATES_BRIEF (handoff document for the marketing/design lead)
