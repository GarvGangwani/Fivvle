"""Schema tests for Voices phase models."""

from __future__ import annotations

from app.schemas.validation_report import ValidationReport, ValidationReportDraft
from app.schemas.voices import VoicesEvidence, VoicesEvidenceDraft, VoicesOutput


def test_voices_evidence_draft_shape() -> None:
    draft = VoicesEvidenceDraft(
        source_url="https://www.reddit.com/r/india/comments/abc123/title/",
        subreddit="india",
        kind="comment",
        verbatim_quote="I hate paying for this every month",
        pain_pattern="User is frustrated by recurring subscription cost for similar tools.",
        on_target_geography=True,
        signal_strength="strong",
    )
    assert draft.subreddit == "india"


def test_voices_output_empty_with_skipped_reason() -> None:
    out = VoicesOutput(atoms=[], skipped_reason="subreddit_selection_returned_empty")
    assert out.skipped_reason == "subreddit_selection_returned_empty"
    assert out.threads_fetched == 0


def test_voices_output_full_atoms() -> None:
    atom = VoicesEvidence(
        source_url="https://www.reddit.com/r/startups/comments/x/y/",
        subreddit="startups",
        kind="post",
        verbatim_quote="We tried three tools and none worked",
        pain_pattern="Founders report tool sprawl without a working solution.",
        on_target_geography=False,
        signal_strength="moderate",
    )
    out = VoicesOutput(
        atoms=[atom],
        subreddits_searched=["startups"],
        threads_fetched=1,
        comments_fetched=2,
    )
    assert len(out.atoms) == 1
    assert out.skipped_reason is None


def _voices_field_max_length(model: type) -> int:
    prop = model.model_json_schema()["properties"]["voices"]
    if "maxLength" in prop:
        return int(prop["maxLength"])
    for item in prop.get("anyOf", []):
        if "maxLength" in item:
            return int(item["maxLength"])
    raise KeyError("voices maxLength not in schema")


def test_validation_report_voices_field_max_length_lockstep() -> None:
    draft_cap = _voices_field_max_length(ValidationReportDraft)
    final_cap = _voices_field_max_length(ValidationReport)
    assert draft_cap == final_cap == 2500
