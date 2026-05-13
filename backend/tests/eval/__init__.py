"""Eval set for the Fivvle research engine.

Public API — import from here in runner scripts and future B2.4 tooling:

    from tests.eval import EVAL_IDEAS, GOLD_STANDARDS, ValidationReportEval, RUBRIC_VERSION

See README.md for usage guidance and cost reminders before running evals.
"""

from tests.eval.gold_standards import GOLD_STANDARDS, GoldStandard
from tests.eval.ideas import ALLOWED_DOMAINS, EVAL_IDEAS, EvalIdea
from tests.eval.rubric import RUBRIC_VERSION, RubricScore, ValidationReportEval

__all__ = [
    "ALLOWED_DOMAINS",
    "EVAL_IDEAS",
    "GOLD_STANDARDS",
    "RUBRIC_VERSION",
    "EvalIdea",
    "GoldStandard",
    "RubricScore",
    "ValidationReportEval",
]
