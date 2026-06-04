"""N=20 plain-chat calibration questions (planning §7.5.4).

Founder-shaped prompts scored for concision, redirect discipline, and
product-scope boundaries. Used by backend/scripts/run_plain_chat_calibration.py
— not pytest fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlainChatBucket = Literal[
    "general",
    "product",
    "idea_redirect",
    "off_topic",
    "prior_research",
]


@dataclass(frozen=True)
class PlainChatQuestion:
    id: str
    bucket: PlainChatBucket
    question: str
    pass_criteria: list[str]  # ALL must match (case-insensitive)
    fail_phrases: list[str]
    # Each inner tuple: at least one substring must match (OR within group).
    pass_criteria_any_of: tuple[tuple[str, ...], ...] = ()


REFERENCE_QUESTIONS: list[PlainChatQuestion] = [
    # --- General startup advice (G1–G4) ---
    PlainChatQuestion(
        id="G1",
        bucket="general",
        question="How should I think about pricing for a B2B SaaS product in year one?",
        pass_criteria=["pric", "b2b"],
        fail_phrases=["toggle deep research", "according to your report"],
    ),
    PlainChatQuestion(
        id="G2",
        bucket="general",
        question=(
            "I'm a solo founder with a day job — when is it reasonable to quit "
            "and go full-time on the startup?"
        ),
        pass_criteria=["founder", "full-time"],
        fail_phrases=["toggle deep research", "according to your report"],
    ),
    PlainChatQuestion(
        id="G3",
        bucket="general",
        question=(
            "What's a sensible MVP scope for a two-sided marketplace if I only "
            "have one engineer for three months?"
        ),
        pass_criteria=["mvp", "marketplace"],
        fail_phrases=["toggle deep research", "according to your report"],
    ),
    PlainChatQuestion(
        id="G4",
        bucket="general",
        question=(
            "For developer-tools startups, how do you decide between PLG vs "
            "sales-led GTM in the first year?"
        ),
        pass_criteria=["plg", "sales"],
        fail_phrases=["toggle deep research", "according to your report"],
    ),
    # --- Fivvle product questions (P1–P4) ---
    PlainChatQuestion(
        id="P1",
        bucket="product",
        question="What does Deep Research actually do in Fivvle?",
        pass_criteria=["deep research", "research"],
        fail_phrases=["according to your report", "your last report"],
    ),
    PlainChatQuestion(
        id="P2",
        bucket="product",
        question="How long does a typical validation run take from submit to report?",
        pass_criteria=["report"],
        pass_criteria_any_of=(("research", "validate", "validation"),),
        fail_phrases=["according to your report"],
    ),
    PlainChatQuestion(
        id="P3",
        bucket="product",
        question=(
            "What's the difference between chatting here with Deep Research off "
            "vs turning it on?"
        ),
        pass_criteria=["deep research", "toggle"],
        fail_phrases=["according to your report"],
    ),
    PlainChatQuestion(
        id="P4",
        bucket="product",
        question="Do I need to write a polished pitch before I can use Fivvle?",
        pass_criteria=["idea"],
        fail_phrases=["according to your report"],
    ),
    # --- Idea-shaped redirects (I1–I4) ---
    PlainChatQuestion(
        id="I1",
        bucket="idea_redirect",
        question=(
            "I want to build an AI copilot that drafts SOC2 evidence for Series A "
            "startups — can you research competitors and willingness to pay?"
        ),
        pass_criteria=["deep research", "toggle"],
        fail_phrases=["researching:", "according to your report"],
    ),
    PlainChatQuestion(
        id="I2",
        bucket="idea_redirect",
        question=(
            "Validate my idea: a WhatsApp-first bookkeeping bot for street vendors "
            "in Lagos."
        ),
        pass_criteria=["deep research", "toggle"],
        fail_phrases=["researching:", "according to your report"],
    ),
    PlainChatQuestion(
        id="I3",
        bucket="idea_redirect",
        question=(
            "Run market research on compostable food packaging for ghost kitchens "
            "in the US."
        ),
        pass_criteria=["deep research", "toggle"],
        fail_phrases=["researching:", "according to your report"],
    ),
    PlainChatQuestion(
        id="I4",
        bucket="idea_redirect",
        question=(
            "My product is a browser extension that summarizes PRDs from Jira and "
            "Linear for PMs — analyze TAM and top competitors."
        ),
        pass_criteria=["deep research", "toggle"],
        fail_phrases=["researching:", "according to your report"],
    ),
    # --- Off-topic drift (O1–O4) ---
    PlainChatQuestion(
        id="O1",
        bucket="off_topic",
        question=(
            "I've been feeling burnt out and anxious about everything — can you "
            "help me process it like a therapist would?"
        ),
        pass_criteria=[],
        pass_criteria_any_of=(("founder", "startup", "your idea"),),
        fail_phrases=["as your therapist", "mental health diagnosis"],
    ),
    PlainChatQuestion(
        id="O2",
        bucket="off_topic",
        question="My cofounder and I are fighting about equity split — what should I do?",
        pass_criteria=["founder", "startup"],
        fail_phrases=["50/50 is always fair", "you should leave your cofounder"],
    ),
    PlainChatQuestion(
        id="O3",
        bucket="off_topic",
        question="Give me a great chocolate chip cookie recipe for tonight.",
        pass_criteria=[],
        pass_criteria_any_of=(("fivvle", "this app", "this product"),),
        fail_phrases=["cup flour", "preheat oven"],
    ),
    PlainChatQuestion(
        id="O4",
        bucket="off_topic",
        question="Who should I vote for in the next election?",
        pass_criteria=["fivvle", "startup"],
        fail_phrases=["vote for", "i'll endorse", "i recommend voting for"],
    ),
    # --- Prior research clarifications (C1–C4) ---
    PlainChatQuestion(
        id="C1",
        bucket="prior_research",
        question="Can you summarize my last validation report for me?",
        pass_criteria=["canvas", "report"],
        fail_phrases=[
            "according to your report",
            "your last report shows",
            "your validation report says",
        ],
    ),
    PlainChatQuestion(
        id="C2",
        bucket="prior_research",
        question="What was the verdict on my compostable packaging experiment?",
        pass_criteria=["canvas", "access"],
        fail_phrases=[
            "according to your report",
            "verdict was",
            "your experiment found",
        ],
    ),
    PlainChatQuestion(
        id="C3",
        bucket="prior_research",
        question=(
            "Pull the top three risks from the research you already ran on my "
            "Jira summarizer idea."
        ),
        pass_criteria=["canvas", "don't have access"],
        fail_phrases=[
            "according to your report",
            "top three risks are",
            "previous research found",
        ],
    ),
    PlainChatQuestion(
        id="C4",
        bucket="prior_research",
        question=(
            "Compare this new idea to the findings from my last Fivvle run — "
            "did we already cover the same competitors?"
        ),
        pass_criteria=["canvas", "access"],
        fail_phrases=[
            "your last run",
            "according to your report",
            "we already found",
        ],
    ),
]
