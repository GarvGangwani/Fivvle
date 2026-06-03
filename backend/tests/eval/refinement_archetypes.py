"""N=5 refinement calibration archetypes (planning §1 + §4.1).

User messages are verbatim from docs/planning/chat-mode-refinement.md §1.
Used by backend/scripts/run_refinement_calibration.py — not pytest fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RefinementArchetype:
    id: str
    name: str
    user_messages: list[str]
    expected_first_decision: Literal["clarify", "finalize"]
    expected_first_dimensions: set[str] | None
    expected_max_clarify_turns: int
    expected_finalize_traits: list[str]
    expected_pivot_turn: int | None


REFINEMENT_ARCHETYPES: list[RefinementArchetype] = [
    RefinementArchetype(
        id="1A",
        name="vague",
        user_messages=[
            "I want to build something for fitness people.",
            (
                "I have a friend who does CrossFit. She's a coach. She spends 4 hours a week "
                "building workout programs for her clients in Excel and it's a mess."
            ),
            "Just CrossFit coaches. Faster to build.",
        ],
        expected_first_decision="clarify",
        expected_first_dimensions={"problem", "audience"},
        expected_max_clarify_turns=2,
        expected_finalize_traits=["crossfit", "excel"],
        expected_pivot_turn=None,
    ),
    RefinementArchetype(
        id="1B",
        name="overconfident",
        user_messages=[
            "I'm building an AI-powered Salesforce competitor for dentists in Toledo.",
            "Patient management. Toledo is just where I'd start; my dad's a dentist there.",
        ],
        expected_first_decision="clarify",
        expected_first_dimensions={"scope", "contradiction"},
        expected_max_clarify_turns=1,
        expected_finalize_traits=["beachhead", "patient"],
        expected_pivot_turn=None,
    ),
    RefinementArchetype(
        id="1C",
        name="crisp",
        user_messages=[
            (
                "AI assistant for engineering managers that summarizes their team's PRs, "
                "Linear tickets, and Slack discussions into a weekly executive report. "
                "Target: EMs at 50–500-person eng orgs who spend 3+ hours every Friday "
                "writing status updates."
            ),
        ],
        expected_first_decision="finalize",
        expected_first_dimensions=None,
        expected_max_clarify_turns=0,
        expected_finalize_traits=["engineering manager", "weekly"],
        expected_pivot_turn=None,
    ),
    RefinementArchetype(
        id="1D",
        name="contradiction",
        user_messages=[
            "Free productivity app that competes with Notion, makes money from enterprise sales.",
            "Like Notion does. PLG into enterprise.",
        ],
        expected_first_decision="clarify",
        expected_first_dimensions={"contradiction"},
        expected_max_clarify_turns=1,
        expected_finalize_traits=["notion", "plg"],
        expected_pivot_turn=None,
    ),
    RefinementArchetype(
        id="1E",
        name="pivot",
        user_messages=[
            "AI tutor for high schoolers studying for the SAT.",
            (
                "Actually, never mind SAT — AP Bio specifically. My sister is taking it "
                "and the materials suck."
            ),
            "Just the student.",
        ],
        expected_first_decision="clarify",
        expected_first_dimensions=None,
        expected_max_clarify_turns=2,
        expected_finalize_traits=["ap bio", "student"],
        expected_pivot_turn=1,
    ),
]
