# ADR 0004: Multi-Step Single-Agent Research Engine over Multi-Agent Architecture

**Status:** Accepted
**Date:** 2026-05

## Context

The AI research engine is Fivvle's primary differentiator. It takes a refined startup idea and produces a research report by searching real sources, extracting evidence, and synthesizing findings. This is the surface that determines whether founders find Fivvle worth using or whether they go back to "ChatGPT + Google Trends + Carrd."

We considered two architectural approaches:

1. **Multi-step single-agent workflow** — one logical agent that runs through explicit phases (planner, searcher, reader, reflector, synthesizer), each phase being a distinct LLM call with typed inputs and outputs.

2. **Truly multi-agent architecture** — multiple specialized "agents" with distinct roles (Planner Agent, Researcher Agent, Critic Agent, Synthesizer Agent) communicating with each other through a shared workspace, possibly using LangGraph, AutoGen, or CrewAI.

The "multi-agent" framing has a marketing appeal — it sounds sophisticated, modern, AI-forward.

## Decision

We will build the research engine as a **multi-step single-agent workflow** using plain `asyncio` + Pydantic, NOT a multi-agent framework.

The five phases are:
1. **Planner** — one LLM call generates 5-7 research questions tailored to the idea
2. **Searcher** — parallel API calls (Tavily, Reddit free tier, Google Trends, news)
3. **Reader/Extractor** — one LLM call per question extracts evidence from search results
4. **Reflector** — one LLM call decides if more searches are needed (max 1-2 reflection loops)
5. **Synthesizer** — one LLM call produces the final structured ValidationReport with citations

Implementation: hand-rolled in Python with `asyncio.gather()` for parallelism. No LangGraph, AutoGen, or CrewAI.

## Reasoning

**Research has a naturally sequential structure:**
plan questions → search → read → reflect → synthesize. This is a pipeline, not a collaboration. Multi-agent architectures shine when the problem genuinely requires negotiation between specialized components — research isn't that problem.

**Multi-agent burns more tokens for marginal benefit:**
A "Critic Agent" reviewing the Researcher's output is two LLM calls where one well-prompted call would do. At $0.50-$2 per research run, even 30% token overhead becomes meaningful at scale.

**Multi-agent is non-deterministic in a deeper way:**
Two agents negotiating produce different conversations on different runs, even at temperature zero. This makes evaluation, regression testing, and quality monitoring much harder. Single-agent multi-step is essentially a deterministic pipeline — same input, similar output, testable per phase.

**Multi-agent frameworks add abstraction cost:**
LangGraph, AutoGen, and CrewAI each impose their own mental model, debugging surface, and learning curve. For a 2-developer team in a 4-month timeline, debugging the framework's abstractions while also debugging the actual prompts doubles the cognitive load.

**The best research engines in production are mostly multi-step single-agent under the hood:**
Perplexity, Anthropic's research demos, and GPT-Researcher all use variants of the multi-step pipeline pattern, even when their marketing language suggests "multi-agent." The architecture isn't where the differentiation lives.

**Where the actual differentiation lives:**
- The quality of the planner prompt (does it produce sharp, specific research questions?)
- The quality of the reader prompt (does it extract verbatim quotes and specific facts, or does it produce generic summaries?)
- The quality of the synthesizer prompt (does it weave evidence into a coherent narrative without losing citations?)
- The quality of source selection (Tavily for now; expand only when usage data justifies it)

These are prompt engineering problems, not architecture problems. Time spent on multi-agent orchestration is time NOT spent on prompt quality.

## Consequences

**What becomes easier:**
- Each phase has clear inputs, outputs, and a single LLM call to debug
- Testing per phase is straightforward (mock inputs, assert outputs)
- Cost is bounded and predictable per run
- Reasoning about failures is straightforward
- Onboarding new engineers — no framework-specific concepts to learn

**What becomes harder:**
- Adding genuinely concurrent agent collaboration if we ever need it (requires architecture change, not just adding another phase)

**What we accept:**
- The marketing language of "multi-agent" isn't available to us, but the substance of what we build is what matters
- If usage data eventually shows a multi-agent architecture would meaningfully improve a specific bottleneck, we can refactor that piece. We won't preemptively build for it.

## Related

- ARCHITECTURE.md (Sequence Diagram 8b — Agentic Research Engine)
- `.cursorrules` (Research Engine Conventions)
