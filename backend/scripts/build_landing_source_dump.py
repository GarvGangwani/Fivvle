"""Build docs/LANDING_PAGE_SOURCE_DUMP.md — verbatim source for external review."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
DOCS = REPO / "docs"
OUT = DOCS / "LANDING_PAGE_SOURCE_DUMP.md"

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
    use_lang = lang or ("tsx" if suffix in {"tsx", "ts"} else suffix)
    rel = path.relative_to(REPO).as_posix()
    return f"### `{rel}`\n\n{py_block(read(path), use_lang)}"


def main() -> None:
    parts: list[str] = ["# Fivvle Landing Page — Verbatim Source Dump\n\n"]

    # 1
    parts.append(
        "## 1. Landing Page V1 — strategy + copy services — "
        "`backend/app/services/landing_page_service.py`\n\n"
    )
    parts.append(py_block(read(BACKEND / "app/services/landing_page_service.py")))

    # 2
    parts.append(
        "## 2. Landing Page V1 — template definitions, copy fields, template selection — "
        "multiple files\n\n"
    )
    parts.append(file_section(BACKEND / "app/schemas/landing_page.py"))
    parts.append(file_section(FRONTEND / "lib/templates.ts"))
    parts.append(file_section(FRONTEND / "lib/types.ts"))
    parts.append(file_section(FRONTEND / "components/landing-templates/TemplateRenderer.tsx"))
    parts.append(file_section(FRONTEND / "components/landing-templates/template-shared.ts"))
    for name in (
        "DarkPremiumTemplate.tsx",
        "BoldV1Template.tsx",
        "MinimalV3Template.tsx",
        "EditorialSaasTemplate.tsx",
        "AetherTemplate.tsx",
        "AbstractTemplate.tsx",
    ):
        parts.append(
            file_section(FRONTEND / "components/landing-templates" / name)
        )

    # 3
    parts.append(
        "## 3. Landing Page V1 — strategist + copy prompt text — "
        "`backend/app/llm/prompts/landing_page.py`\n\n"
    )
    parts.append(py_block(read(BACKEND / "app/llm/prompts/landing_page.py")))

    # 4
    parts.append(
        "## 4. Landing Page Runtime V2 — four LLM pipeline stages + prompts — "
        "multiple files\n\n"
    )
    parts.append(file_section(BACKEND / "app/services/landing_page_v2_service.py"))
    for prompt in (
        "landing_page_v2_narrative.py",
        "landing_page_v2_creative.py",
        "landing_page_v2_visual.py",
        "landing_page_v2_component.py",
    ):
        parts.append(file_section(BACKEND / "app/llm/prompts" / prompt))

    # 5
    parts.append(
        "## 5. Landing Page V2 — design_tokens, component schema — "
        "`backend/app/schemas/landing_page_v2.py` + `frontend/lib/landing-page-v2-types.ts`\n\n"
    )
    parts.append(file_section(BACKEND / "app/schemas/landing_page_v2.py"))
    parts.append(file_section(FRONTEND / "lib/landing-page-v2-types.ts"))

    # 6
    parts.append(
        "## 6. SQLAlchemy models — `LandingPage` + `LandingPageV2Spec`\n\n"
    )
    parts.append(file_section(BACKEND / "app/db/models/landing_page.py"))
    parts.append(file_section(BACKEND / "app/db/models/landing_page_v2.py"))

    # 7
    parts.append(
        "## 7. PageView + WaitlistSignup models and tracking endpoints\n\n"
    )
    parts.append(file_section(BACKEND / "app/db/models/page_view.py"))
    parts.append(file_section(BACKEND / "app/db/models/waitlist_signup.py"))
    parts.append(file_section(BACKEND / "app/routers/public.py"))
    parts.append(file_section(BACKEND / "app/services/waitlist_service.py"))
    parts.append(file_section(FRONTEND / "app/e/[slug]/page.tsx"))
    parts.append(file_section(FRONTEND / "lib/landing-host.ts"))
    parts.append(file_section(FRONTEND / "lib/published-page.ts"))
    parts.append(file_section(FRONTEND / "lib/api.ts"))

    # 8
    parts.append("## 8. Social distribution / reels / external platform posting\n\n")
    parts.append(
        "No backend or frontend code exists for posting reels to Instagram, YouTube, "
        "LinkedIn, X/Twitter, Reddit, or Discord APIs.\n\n"
    )
    parts.append(file_section(FRONTEND / "components/distribution/ShareLinksPanel.tsx"))
    parts.append(file_section(FRONTEND / "components/distribution/DistributeSection.tsx"))

    # 9
    parts.append("## 9. ADR 0005 — Landing Page V1 templates — `docs/adr/0005-templates-not-ai-generated.md`\n\n")
    parts.append(py_block(read(DOCS / "adr/0005-templates-not-ai-generated.md"), "markdown"))

    # 10
    parts.append("## 10. ADR or planning doc for Landing Page Runtime V2\n\n")
    parts.append("No dedicated ADR exists for Landing Page Runtime V2.\n\n")

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
