"""Build docs/INSIGHT_EVIDENCE_SOURCE_DUMP.md — verbatim source for external review."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
DOCS = REPO / "docs"
OUT = DOCS / "INSIGHT_EVIDENCE_SOURCE_DUMP.md"

FENCE = "```"


def read(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8")


def py_block(content: str, lang: str = "python") -> str:
    return f"{FENCE}{lang}\n{content.rstrip()}\n{FENCE}\n\n"


def file_section(path: Path, *, lang: str | None = None) -> str:
    suffix = path.suffix.lstrip(".")
    use_lang = lang or suffix
    rel = path.relative_to(REPO).as_posix()
    return f"### `{rel}`\n\n{py_block(read(path), use_lang)}"


def enum_excerpt(path: Path, class_names: list[str]) -> str:
    """Extract named enum class blocks from a module (verbatim lines)."""
    lines = read(path).splitlines()
    chunks: list[str] = []
    for class_name in class_names:
        start: int | None = None
        for i, line in enumerate(lines):
            if line.startswith(f"class {class_name}"):
                start = i
                break
        if start is None:
            continue
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if lines[j].startswith("class ") and not lines[j].startswith("class _"):
                end = j
                break
        chunks.append("\n".join(lines[start:end]).rstrip())
    return "\n\n\n".join(chunks)


def main() -> None:
    parts: list[str] = ["# Fivvle Insight, Evidence, Chat, Wallet — Verbatim Source Dump\n\n"]

    # 1
    parts.append(
        "## 1. Evidence atoms — `collect_evidence_atoms()` — "
        "`backend/app/services/evidence_atoms.py`\n\n"
    )
    parts.append(py_block(read(BACKEND / "app/services/evidence_atoms.py")))
    parts.append(file_section(BACKEND / "app/schemas/reader.py"))
    parts.append(file_section(BACKEND / "app/schemas/business_construction.py"))

    # 2
    parts.append(
        "## 2. Insight Report generation — "
        "`backend/app/services/insight_service.py`\n\n"
    )
    parts.append(file_section(BACKEND / "app/services/insight_service.py"))
    parts.append(file_section(BACKEND / "app/llm/prompts/insight.py"))
    parts.append(file_section(BACKEND / "app/schemas/insight.py"))

    # 3
    parts.append(
        "## 3. InsightReport SQLAlchemy model — "
        "`backend/app/db/models/insight_report.py`\n\n"
    )
    parts.append(py_block(read(BACKEND / "app/db/models/insight_report.py")))

    # 4
    parts.append(
        "## 4. Traffic-source attribution and conversion-rate calculation — "
        "`backend/app/services/analytics_aggregator.py`\n\n"
    )
    parts.append(file_section(BACKEND / "app/services/analytics_aggregator.py"))
    parts.append(file_section(BACKEND / "app/services/experiment_dashboard_stats.py"))

    # 5
    parts.append(
        "## 5. ChatThread / ChatMessage models and message editing — "
        "multiple files\n\n"
    )
    parts.append(
        "No message-forking implementation exists in the repository.\n\n"
    )
    parts.append(file_section(BACKEND / "app/db/models/chat_thread.py"))
    parts.append(file_section(BACKEND / "app/db/models/chat_message.py"))
    parts.append(file_section(BACKEND / "app/db/models/chat_attachment.py"))
    parts.append(file_section(BACKEND / "app/services/chat_service.py"))
    parts.append(file_section(BACKEND / "app/routers/chat.py"))
    parts.append(file_section(BACKEND / "app/schemas/chat.py"))

    # 6
    parts.append(
        "## 6. Wallet, WalletTransaction, Coupon, CouponRedemption, PaymentOrder models\n\n"
    )
    for name in (
        "wallet.py",
        "wallet_transaction.py",
        "coupon.py",
        "coupon_redemption.py",
        "payment_order.py",
    ):
        parts.append(file_section(BACKEND / "app/db/models" / name))

    # 7
    parts.append(
        "## 7. Experiment SQLAlchemy model — "
        "`backend/app/db/models/experiment.py`\n\n"
    )
    parts.append(py_block(read(BACKEND / "app/db/models/experiment.py")))
    parts.append(
        "### `backend/app/db/enums.py` — `ExperimentStatus`, `DispatchTrigger`\n\n"
    )
    parts.append(
        py_block(
            enum_excerpt(
                BACKEND / "app/db/enums.py",
                ["ExperimentStatus", "DispatchTrigger"],
            )
        )
    )

    # 8
    parts.append(
        "## 8. Sentiment-analysis or comment-analysis for distributed content\n\n"
    )
    parts.append(
        "No sentiment-analysis or comment-analysis code exists for engagement or "
        "comments on distributed content (Instagram, YouTube, LinkedIn, X, Reddit, "
        "Discord, etc.).\n\n"
    )

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
