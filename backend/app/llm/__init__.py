"""LLM layer — wrapper, pricing, prompt templates.

Public API:
    complete            — plain-text completion
    complete_structured — Pydantic-typed completion via Instructor
    LLMResult           — result envelope
    compute_cost_usd    — pricing helper (rarely called directly)
"""

from app.llm.client import LLMResult, complete, complete_structured
from app.llm.cost import compute_cost_usd, is_known_model

__all__ = [
    "LLMResult",
    "complete",
    "complete_structured",
    "compute_cost_usd",
    "is_known_model",
]
