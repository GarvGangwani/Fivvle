"""LLM prompt templates.

Real prompts arrive in:
- Build step 7: refinement prompt (idea → structured refined idea)
- Build step 8: research engine prompts (planner, reader, reflector, synthesizer)
- Build step 11: landing page selection prompt

Per AGENTS.md "LLM and agent security", every prompt that consumes
web-scraped or user-supplied content MUST use clear data/instruction
separation. See the example template in AGENTS.md.
"""
