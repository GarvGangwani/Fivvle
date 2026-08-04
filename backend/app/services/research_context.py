"""Validation-report research substrate for the master rail (post–research-agent).

Builds a citation ``source_index`` and a capped findings digest so the master
can answer research questions natively with ``[cite:sN]`` markers.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_CITE_SOURCE_ID_RE = re.compile(r"\[cite:\s*(s\d+)\]", re.IGNORECASE)

# Soft token budget for findings_digest (chars, not tokens).
_FINDINGS_DIGEST_MAX_CHARS = 6000
_CLAIM_MAX = 400
_COMPETITOR_BLURB_MAX = 280


def _domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host or url
    except Exception:
        return url


def _truncate(text: str, max_len: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _iter_report_citations(report: dict[str, Any]) -> list[dict[str, str]]:
    """Collect Citation-shaped dicts from findings + competitors (dedupe by URL)."""
    collected: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def _add(cite: Any) -> None:
        if not isinstance(cite, dict):
            return
        url = cite.get("url")
        if not isinstance(url, str) or not url.strip():
            return
        url = url.strip()
        if url in seen_urls:
            return
        seen_urls.add(url)
        title = cite.get("title")
        domain = cite.get("source_domain")
        collected.append(
            {
                "source_title": title.strip()
                if isinstance(title, str) and title.strip()
                else url,
                "source_url": url,
                "source_domain": domain.strip()
                if isinstance(domain, str) and domain.strip()
                else _domain_from_url(url),
            }
        )

    for qf in report.get("questions_and_findings") or []:
        if not isinstance(qf, dict):
            continue
        for finding in qf.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            for cite in finding.get("citations") or []:
                _add(cite)

    for comp in report.get("competitors") or []:
        if not isinstance(comp, dict):
            continue
        for cite in comp.get("citations") or []:
            _add(cite)

    return collected


def build_source_index(
    report: dict[str, Any] | None,
) -> dict[str, dict[str, str | None]]:
    """Map ``s1``..``sN`` -> primary source metadata from the validation report."""
    if not report:
        return {}
    index: dict[str, dict[str, str | None]] = {}
    for i, cite in enumerate(_iter_report_citations(report), start=1):
        source_id = f"s{i}"
        index[source_id] = {
            "source_title": cite["source_title"],
            "source_url": cite["source_url"],
            "source_domain": cite["source_domain"],
        }
    return index


def build_source_refs_from_cite_ids(
    text: str,
    source_index: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    """Resolve in-content ``[cite:sN]`` markers via ``source_index``."""
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _CITE_SOURCE_ID_RE.finditer(text):
        source_id = match.group(1).lower()
        if source_id in seen:
            continue
        meta = source_index.get(source_id)
        if meta is None:
            continue
        seen.add(source_id)
        marker_id = f"[cite:{source_id}]"
        refs.append(
            {
                "marker_id": marker_id,
                "source_title": meta.get("source_title") or source_id,
                "source_url": meta.get("source_url"),
                "source_domain": meta.get("source_domain"),
            }
        )
    return refs


def source_refs_from_index(
    source_index: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    """Full source_refs list for a tool_result (every indexed source)."""
    refs: list[dict[str, Any]] = []
    for source_id, meta in source_index.items():
        refs.append(
            {
                "marker_id": f"[cite:{source_id}]",
                "source_title": meta.get("source_title") or source_id,
                "source_url": meta.get("source_url"),
                "source_domain": meta.get("source_domain"),
            }
        )
    return refs


def build_findings_digest(report: dict[str, Any]) -> str:
    """Capped textual digest of findings + competitors for the master."""
    parts: list[str] = []

    rec = report.get("overall_recommendation")
    if isinstance(rec, str) and rec.strip():
        parts.append(f"Overall recommendation: {rec.strip()}")

    for qf in report.get("questions_and_findings") or []:
        if not isinstance(qf, dict):
            continue
        qid = qf.get("question_id") or "?"
        question = qf.get("question")
        q_line = f"Q[{qid}]"
        if isinstance(question, str) and question.strip():
            q_line += f": {_truncate(question, 200)}"
        parts.append(q_line)
        for finding in qf.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            claim = finding.get("claim") or finding.get("finding")
            if not isinstance(claim, str) or not claim.strip():
                continue
            conf = finding.get("confidence")
            conf_s = f" ({conf})" if isinstance(conf, str) else ""
            parts.append(f"  - {_truncate(claim, _CLAIM_MAX)}{conf_s}")

    comps = report.get("competitors") or []
    if comps:
        parts.append("Competitors:")
        for comp in comps:
            if not isinstance(comp, dict):
                continue
            name = comp.get("name") or comp.get("competitor_name") or "Unknown"
            blurb = (
                comp.get("summary")
                or comp.get("description")
                or comp.get("positioning")
                or ""
            )
            if isinstance(blurb, str) and blurb.strip():
                parts.append(f"  - {name}: {_truncate(blurb, _COMPETITOR_BLURB_MAX)}")
            else:
                parts.append(f"  - {name}")

    digest = "\n".join(parts).strip()
    if len(digest) > _FINDINGS_DIGEST_MAX_CHARS:
        digest = digest[: _FINDINGS_DIGEST_MAX_CHARS - 3].rstrip() + "..."
    return digest


def format_sources_block(source_index: dict[str, dict[str, str | None]]) -> str:
    """Render ``<sources>`` body lines (kept for prompt assembly if needed)."""
    lines: list[str] = []
    for source_id, meta in source_index.items():
        title = meta.get("source_title") or source_id
        url = meta.get("source_url") or ""
        domain = meta.get("source_domain") or ""
        lines.append(f"{source_id}: {title} | {url} | {domain}")
    return "\n".join(lines)
