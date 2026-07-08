"""Load upstream and Reddit fixtures for voices_devloop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.integrations.perplexity import PerplexityResult
from app.integrations.reddit import RedditComment, RedditPost
from app.schemas.business_construction import (
    EvidenceAnalysisResult,
    ReasoningEngineOutput,
)
from app.schemas.planner import ResearchPlan
from app.schemas.reader import ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.targeting import ExperimentTargeting
from app.schemas.voices import VoicesOutput
from app.services.synthesizer_input import CitationHydrationEntry

_PACKAGE_ROOT = Path(__file__).resolve().parent
FIXTURES_ROOT = _PACKAGE_ROOT / "fixtures"


def upstream_dir(name: str) -> Path:
    return FIXTURES_ROOT / f"upstream_{name}"


def perplexity_dir(mode: str) -> Path:
    return FIXTURES_ROOT / f"perplexity_{mode}"


def reddit_dir(mode: str) -> Path:
    return FIXTURES_ROOT / f"reddit_{mode}"


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_upstream(name: str) -> dict[str, Any]:
    base = upstream_dir(name)
    refined = RefinedIdea.model_validate(_read_json(base / "refined_idea.json"))
    plan = ResearchPlan.model_validate(_read_json(base / "research_plan.json"))
    reader_path = base / "reflected_outputs.json"
    if not reader_path.exists():
        reader_path = base / "reader_outputs.json"
    reader_raw = _read_json(reader_path)
    reader_outputs = {
        key: ReaderOutput.model_validate(value) for key, value in reader_raw.items()
    }
    targeting_raw = _read_json(base / "targeting.json")
    targeting = (
        ExperimentTargeting.model_validate(targeting_raw)
        if targeting_raw is not None
        else None
    )
    evidence_raw = _read_json(base / "evidence_analysis.json")
    evidence_analysis = (
        EvidenceAnalysisResult.model_validate(evidence_raw)
        if evidence_raw is not None
        else None
    )
    reasoning_raw = _read_json(base / "reasoning_output.json")
    reasoning_output = (
        ReasoningEngineOutput.model_validate(reasoning_raw)
        if reasoning_raw is not None
        else None
    )
    return {
        "refined_idea": refined,
        "research_plan": plan,
        "reader_outputs": reader_outputs,
        "targeting": targeting,
        "evidence_analysis": evidence_analysis,
        "reasoning_output": reasoning_output,
    }


def load_perplexity_results_by_subreddit(mode: str) -> dict[str, list[PerplexityResult]]:
    raw = _read_json(perplexity_dir(mode) / "results_by_subreddit.json")
    return {
        sub: [PerplexityResult(**item) for item in items]
        for sub, items in raw.items()
    }


def load_reddit_posts(mode: str) -> list[RedditPost]:
    raw = _read_json(reddit_dir(mode) / "subreddit_posts.json")
    return [RedditPost.model_validate(item) for item in raw]


def load_reddit_comments(mode: str) -> dict[str, list[RedditComment]]:
    raw = _read_json(reddit_dir(mode) / "post_comments.json")
    return {
        post_id: [RedditComment.model_validate(item) for item in comments]
        for post_id, comments in raw.items()
    }


def scratch_experiment_id() -> UUID:
    """Existing experiment row for LLMCall FK during dev-loop runs."""
    return UUID("62ce7480-834b-4568-a024-8c15ef71f5d6")


def build_citation_index_from_reader_outputs(
    reader_outputs: dict[str, ReaderOutput],
) -> dict[str, CitationHydrationEntry]:
    """Build citation hydration index from Reader evidence URLs (harness fallback)."""
    from app.services.synthesizer_service import _extract_domain

    index: dict[str, CitationHydrationEntry] = {}
    for output in reader_outputs.values():
        for atom in output.extracted_evidence:
            if atom.source_url in index:
                continue
            index[atom.source_url] = CitationHydrationEntry(
                title=atom.source_url[:500],
                source_domain=_extract_domain(atom.source_url)[:255],
            )
    return index


def build_citation_index_for_harness(
    reader_outputs: dict[str, ReaderOutput],
    voices_output: VoicesOutput,
) -> dict[str, CitationHydrationEntry]:
    """Reader URLs plus Voices atom URLs (fixtures include Reddit permalinks)."""
    index = build_citation_index_from_reader_outputs(reader_outputs)
    for atom in voices_output.atoms:
        if atom.source_url in index:
            continue
        index[atom.source_url] = CitationHydrationEntry(
            title=f"r/{atom.subreddit}"[:500],
            source_domain="reddit.com",
        )
    return index
