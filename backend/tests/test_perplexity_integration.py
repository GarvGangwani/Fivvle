"""Unit tests for Perplexity integration response parsing."""

from __future__ import annotations

from app.integrations.perplexity import _parse_search_results


def test_parse_search_results_primary() -> None:
    raw = {
        "search_results": [
            {
                "title": "Example",
                "url": "https://www.reddit.com/r/startups/comments/1/",
                "snippet": "A snippet",
                "date": "2024-01-01",
            }
        ]
    }
    results = _parse_search_results(raw, max_results=5)
    assert len(results) == 1
    assert results[0].title == "Example"
    assert results[0].snippet == "A snippet"
    assert results[0].date == "2024-01-01"


def test_parse_falls_back_to_citations() -> None:
    raw = {"citations": ["https://www.reddit.com/r/startups/comments/2/"]}
    results = _parse_search_results(raw, max_results=5)
    assert len(results) == 1
    assert results[0].url.endswith("/comments/2/")
    assert results[0].snippet == ""
