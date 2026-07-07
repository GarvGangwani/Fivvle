"""Build docs/context/FIVVLE_CODEBASE_CONTEXT.md for external assistants."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = REPO / "docs" / "context" / "FIVVLE_CODEBASE_CONTEXT.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "<REDACTED>"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "<REDACTED>"),
    (re.compile(r"gsk_[A-Za-z0-9]{20,}"), "<REDACTED>"),
    (re.compile(r"tvly-[A-Za-z0-9]{20,}"), "<REDACTED>"),
    (re.compile(r"-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----"), "<REDACTED>"),
    (re.compile(r'"private_key"\s*:\s*"[^"]*"'), '"private_key": "<REDACTED>"'),
    (re.compile(r'"client_email"\s*:\s*"[^"]*@[^"]*"'), '"client_email": "<REDACTED>"'),
]

CONFIG_SECRET_FIELDS = {
    "anthropic_api_key",
    "groq_api_key",
    "kimi_api_key",
    "tavily_api_key",
    "reddit_client_secret",
    "razorpay_key_secret",
    "razorpay_webhook_secret",
    "database_url",
    "firebase_service_account_path",
    "sentry_dsn",
    "research_dispatcher_hmac_secret",
    "internal_api_secret",
}


def redact(text: str, *, config_mode: bool = False) -> str:
    out = text
    for pat, repl in SECRET_PATTERNS:
        out = pat.sub(repl, out)
    if config_mode:
        for field in CONFIG_SECRET_FIELDS:
            out = re.sub(
                rf'^(\s*{re.escape(field)}\s*:\s*)(.+)$',
                r"\1<REDACTED>",
                out,
                flags=re.MULTILINE,
            )
            out = re.sub(
                rf'^(\s*{re.escape(field.upper())}\s*=\s*)(.+)$',
                r"\1<REDACTED>",
                out,
                flags=re.MULTILINE,
            )
    return out


def lang_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".json": "json",
        ".toml": "toml",
        ".ini": "ini",
        ".md": "markdown",
    }.get(ext, "text")


def fence(path: str, content: str, *, config_mode: bool = False) -> str:
    body = redact(content, config_mode=config_mode)
    lg = lang_for(path)
    return f"```{lg} title=\"{path}\"\n{body.rstrip()}\n```\n\n"


def heading(title: str) -> str:
    return f"{title}\n\n"


def file_section(path: str, *, repo_rel: bool = True, config_mode: bool = False) -> str:
    full = REPO / path if repo_rel else Path(path)
    rel = path.replace("\\", "/")
    hdr = f"### `{rel}`\n\n"
    if not full.is_file():
        return hdr + "DOES NOT EXIST\n\n"
    try:
        content = full.read_text(encoding="utf-8")
    except OSError:
        return hdr + "DOES NOT EXIST\n\n"
    return hdr + fence(rel, content, config_mode=config_mode)


def run_cmd(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd or REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return out.strip() or "(no output)"
    except FileNotFoundError:
        return f"(command not found: {cmd[0]})"


def tree_lines(root: Path, max_depth: int = 3, _depth: int = 0, _prefix: str = "") -> list[str]:
    if not root.exists():
        return [f"{root.name}  [DOES NOT EXIST]"]
    lines: list[str] = []
    if _depth == 0:
        lines.append(root.name + "/")
    if _depth >= max_depth:
        return lines
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return lines
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        branch = "└── " if is_last else "├── "
        lines.append(f"{_prefix}{branch}{entry.name}{'/' if entry.is_dir() else ''}")
        if entry.is_dir() and _depth + 1 < max_depth:
            extension = "    " if is_last else "│   "
            lines.extend(tree_lines(entry, max_depth, _depth + 1, _prefix + extension))
    return lines


def grep_repo(pattern: str, *paths: str) -> str:
    results: list[str] = []
    for rel in paths:
        base = REPO / rel
        if not base.exists():
            results.append(f"# {rel}: DOES NOT EXIST")
            continue
        if base.is_file():
            files = [base]
        else:
            files = sorted(base.rglob("*.py"))
        rx = re.compile(pattern)
        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8")
            except OSError:
                continue
            rel_fp = fp.relative_to(REPO).as_posix()
            for lineno, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    results.append(f"{rel_fp}:{lineno}:{line}")
    return "\n".join(results) if results else "(no matches)"


def extract_llm_client_section() -> str:
    client_path = ROOT / "app" / "llm" / "client.py"
    text = client_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Module docstring (lines 1-17)
    doc_end = 0
    if lines and lines[0].startswith('"""'):
        for i, line in enumerate(lines):
            if i > 0 and '"""' in line:
                doc_end = i
                break
    module_doc = "\n".join(lines[: doc_end + 1])

    # Public classes / functions with signatures + docstrings
    public_blocks: list[str] = []
    i = 0
    public_names = {
        "class CacheBreakpoint",
        "class LLMResult",
        "async def complete(",
        "async def complete_with_image(",
        "async def complete_structured(",
    }
    while i < len(lines):
        line = lines[i]
        matched = None
        for name in public_names:
            if line.startswith(name.split("(")[0].replace("async def ", "async def ")):
                if name.startswith("class") and line.startswith(name.split("(")[0]):
                    matched = name.split("(")[0]
                elif name.startswith("async def") and line.startswith(name.split("(")[0] + "("):
                    matched = name.split("(")[0] + "("
        if matched:
            block = [line]
            i += 1
            if '"""' in line and line.count('"""') == 1:
                while i < len(lines):
                    block.append(lines[i])
                    if '"""' in lines[i]:
                        i += 1
                        break
                    i += 1
            elif i < len(lines) and lines[i].strip().startswith('"""'):
                while i < len(lines):
                    block.append(lines[i])
                    if lines[i].strip().endswith('"""') and lines[i].count('"""') >= 1:
                        i += 1
                        break
                    i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("async def ") or (
                    nxt.startswith("def ") and not nxt.startswith("def _")
                ) or nxt.startswith("class "):
                    break
                if nxt.strip() == "" and i + 1 < len(lines) and (
                    lines[i + 1].startswith("async def ")
                    or lines[i + 1].startswith("def ")
                    or lines[i + 1].startswith("class ")
                ):
                    break
                block.append(nxt)
                i += 1
            public_blocks.append("\n".join(block))
            continue
        i += 1

    parts = [
        heading("### `backend/app/llm/client.py` (1056 lines — excerpts per spec)"),
        fence("backend/app/llm/client.py [module docstring]", module_doc + "\n"),
        heading("#### Public API signatures and docstrings"),
    ]
    for block in public_blocks:
        parts.append(fence("backend/app/llm/client.py [excerpt]", block + "\n"))
    parts.append(
        heading(
            "#### Note: full implementation omitted; all LLM calls MUST go through this module."
        )
    )
    return "".join(parts)


def adr_include_body(filename: str) -> bool:
    title = filename.lower()
    keywords = (
        "pipeline",
        "planner",
        "reader",
        "synthesizer",
        "reflector",
        "experiment",
        "refine",
        "prompt",
        "evidence",
        "search",
        "research",
        "dispatch",
    )
    skip_keywords = ("payment", "wallet", "brand", "css-module")
    if any(k in title for k in skip_keywords):
        return False
    if "landing-page" in title and "v2" in title:
        return False
    return any(k in title for k in keywords)


def adr_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parts: list[str] = [
        "# Fivvle Codebase Context\n\n",
        "Generated for external assistant — verbatim sources, secrets redacted.\n\n",
    ]

    # --- Section 1 ---
    parts.append(heading("## 1. Repo orientation"))
    parts.append("### git rev-parse HEAD\n\n```text\n")
    parts.append(run_cmd(["git", "rev-parse", "HEAD"]))
    parts.append("\n```\n\n")
    parts.append("### git branch --show-current\n\n```text\n")
    parts.append(run_cmd(["git", "branch", "--show-current"]))
    parts.append("\n```\n\n")
    parts.append("### git ls-files | wc -l\n\n```text\n")
    count = run_cmd(["git", "ls-files"])
    parts.append(str(len(count.splitlines())) if count != "(no output)" else count)
    parts.append("\n```\n\n")
    parts.append("### tree -L 3 backend/app\n\n```text\n")
    parts.append("\n".join(tree_lines(REPO / "backend" / "app", 3)))
    parts.append("\n```\n\n")
    parts.append("### tree -L 3 frontend\n\n```text\n")
    parts.append("\n".join(tree_lines(REPO / "frontend", 3)))
    parts.append("\n```\n\n")

    # --- Section 2 ---
    parts.append(heading("## 2. Dependency manifests"))
    for p in (
        "backend/pyproject.toml",
        "backend/alembic.ini",
        "frontend/package.json",
    ):
        parts.append(file_section(p))

    # --- Section 3 ---
    parts.append(heading("## 3. Experiment model + schemas + API"))
    for p in (
        "backend/app/db/models/experiment.py",
        "backend/app/db/base.py",
        "backend/app/db/enums.py",
        "backend/app/schemas/experiment.py",
        "backend/app/routers/experiments.py",
        "backend/app/services/experiment_service.py",
    ):
        parts.append(file_section(p))
    parts.append(heading("### grep -rn \"class Experiment\" backend/app"))
    parts.append("```text\n")
    parts.append(grep_repo(r"class Experiment", "backend/app"))
    parts.append("\n```\n\n")

    # --- Section 4 ---
    parts.append(heading("## 4. Alembic"))
    parts.append(file_section("backend/alembic/env.py"))
    migrations = sorted((REPO / "backend" / "alembic" / "versions").glob("*.py"))
    migrations = [m for m in migrations if m.name != "__init__.py"]
    for m in migrations[-3:]:
        parts.append(file_section(f"backend/alembic/versions/{m.name}"))
    parts.append("### alembic heads\n\n```text\n")
    parts.append(run_cmd(["uv", "run", "alembic", "heads"], cwd=ROOT))
    parts.append("\n```\n\n")
    parts.append("### alembic current\n\n```text\n")
    parts.append(run_cmd(["uv", "run", "alembic", "current"], cwd=ROOT))
    parts.append("\n```\n\n")

    # --- Section 5 ---
    parts.append(heading("## 5. Research pipeline — FULL files"))
    pipeline_files = [
        "backend/app/services/planner_service.py",
        "backend/app/services/searcher_service.py",
        "backend/app/services/reader_service.py",
        "backend/app/services/reflector_service.py",
        "backend/app/services/synthesizer_service.py",
        "backend/app/services/research_engine.py",
        "backend/app/services/research_engine_service.py",
        "backend/app/services/synthesizer_input.py",
        "backend/app/services/research_phase_mapping.py",
        "backend/app/services/evidence_atoms.py",
        "backend/app/llm/prompts/planner.py",
        "backend/app/llm/prompts/reader.py",
        "backend/app/llm/prompts/reflector_query_refinement.py",
        "backend/app/llm/prompts/synthesizer.py",
        "backend/app/integrations/tavily.py",
        "backend/app/schemas/planner.py",
        "backend/app/schemas/search.py",
        "backend/app/schemas/reader.py",
        "backend/app/schemas/reflector.py",
        "backend/app/schemas/validation_report.py",
        "backend/app/db/models/validation_report.py",
        "backend/app/services/dispatch_service.py",
        "backend/app/dispatchers/protocol.py",
        "backend/app/dispatchers/factory.py",
        "backend/app/dispatchers/in_process.py",
        "backend/app/dispatchers/http.py",
    ]
    for p in pipeline_files:
        parts.append(file_section(p))

    parts.append(heading("### find backend -name \"*.txt\" -o -name \"*prompt*\""))
    txt_files = sorted(REPO.glob("backend/**/*.txt"))
    prompt_files = sorted(REPO.glob("backend/**/*prompt*"))
    find_lines = [str(p.relative_to(REPO)).replace("\\", "/") for p in txt_files + prompt_files]
    parts.append("```text\n" + ("\n".join(find_lines) if find_lines else "(no matches)") + "\n```\n\n")
    for p in find_lines:
        if p.endswith(".py") and "alembic" not in p:
            continue  # already included above or not a prompt source
        if p.endswith(".txt"):
            parts.append(file_section(p))

    # --- Section 6 ---
    parts.append(heading("## 6. Business Construction Engine"))
    for p in (
        "backend/app/schemas/business_construction.py",
        "backend/app/services/evidence_atoms.py",
        "backend/app/services/evidence_analysis_service.py",
        "backend/app/services/reasoning_engine_service.py",
    ):
        parts.append(file_section(p))

    # --- Section 7 ---
    parts.append(heading("## 7. Refine flow"))
    for p in (
        "backend/app/services/refinement_service.py",
        "backend/app/llm/prompts/refinement.py",
        "backend/app/services/chat_service.py",
        "backend/app/db/models/chat_thread.py",
        "backend/app/db/models/chat_message.py",
        "backend/app/schemas/chat.py",
        "backend/app/schemas/refinement.py",
        "backend/app/routers/chat.py",
        "frontend/app/(dashboard)/experiment/[id]/page.tsx",
        "frontend/components/refinement/RefineStagePanel.tsx",
        "frontend/components/chat/ChatInterface.tsx",
        "frontend/components/research/ReportCanvas.tsx",
        "frontend/components/dashboard/ExperimentDetailPanel.tsx",
    ):
        parts.append(file_section(p))

    # --- Section 8 ---
    parts.append(heading("## 8. Experiment status / state"))
    parts.append(file_section("backend/app/db/enums.py"))
    parts.append(file_section("backend/app/services/research_phase_mapping.py"))
    parts.append(
        heading(
            '### grep -rn "experiment.status\\|status =" backend/app/services backend/app/pipeline'
        )
    )
    parts.append("```text\n")
    parts.append("# backend/app/pipeline: DOES NOT EXIST\n")
    parts.append(grep_repo(r"experiment\.status|status\s*=", "backend/app/services"))
    parts.append("\n```\n\n")

    # --- Section 9 ---
    parts.append(heading("## 9. LLM call layer"))
    parts.append(extract_llm_client_section())
    parts.append(file_section("backend/app/db/models/llm_call.py"))

    # --- Section 10 ---
    parts.append(heading("## 10. ADRs"))
    adr_dir = REPO / "docs" / "adr"
    parts.append("### ls docs/adr/\n\n```text\n")
    adr_files = sorted(adr_dir.glob("*.md"))
    parts.append("\n".join(f.name for f in adr_files))
    parts.append("\n```\n\n")
    for adr in adr_files:
        if adr.name == "README.md":
            continue
        title = adr_title(adr)
        rel = f"docs/adr/{adr.name}"
        if adr_include_body(adr.name) or adr_include_body(title.lower()):
            parts.append(f"### {title} — `{rel}`\n\n")
            parts.append(fence(rel, adr.read_text(encoding="utf-8")))
        else:
            parts.append(f"- **{title}** (`{rel}`) — body omitted (unrelated to research/refine scope)\n")

    # --- Section 11 ---
    parts.append(heading("## 11. Config and settings"))
    parts.append(file_section("backend/app/config.py", config_mode=True))

    # --- Section 12 ---
    parts.append(heading("## 12. Tests"))
    test_patterns = ("pipeline", "planner", "synthesizer", "experiment", "refine")
    test_root = REPO / "backend" / "tests"
    matched_tests: list[str] = []
    for tp in test_patterns:
        for f in sorted(test_root.rglob(f"test_*{tp}*")):
            if "__pycache__" in f.parts or f.suffix != ".py":
                continue
            rel = f.relative_to(REPO).as_posix()
            if rel not in matched_tests:
                matched_tests.append(rel)
    parts.append("### Matching test files\n\n```text\n")
    parts.append("\n".join(matched_tests) if matched_tests else "(none)")
    parts.append("\n```\n\n")
    parts.append(heading("### Representative pipeline test: `backend/tests/services/test_planner_service.py`"))
    parts.append(file_section("backend/tests/services/test_planner_service.py"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(parts)
    OUT.write_text(content, encoding="utf-8")
    line_count = content.count("\n") + (0 if content.endswith("\n") else 1)
    print(f"Wrote {OUT}")
    print(f"Bytes: {OUT.stat().st_size}")
    print(f"Lines: {line_count}")


if __name__ == "__main__":
    main()
