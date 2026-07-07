"""Build docs/context/FIVVLE_FRONTEND_CONTEXT.md for external UX assistants."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"
OUT = REPO / "docs" / "context" / "FIVVLE_FRONTEND_CONTEXT.md"


def redact(text: str) -> str:
    patterns: list[tuple[str, str]] = [
        (r"(NEXT_PUBLIC_FIREBASE_API_KEY\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r"(NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r"(NEXT_PUBLIC_FIREBASE_PROJECT_ID\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r"(NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r"(NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r"(NEXT_PUBLIC_FIREBASE_APP_ID\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r"(NEXT_PUBLIC_API_URL\s*=\s*)[^\n]+", r"\1<REDACTED>"),
        (r'("apiKey"\s*:\s*)"[^"]+"', r'\1"<REDACTED>"'),
        (r'("authDomain"\s*:\s*)"[^"]+"', r'\1"<REDACTED>"'),
        (r'("projectId"\s*:\s*)"[^"]+"', r'\1"<REDACTED>"'),
        (r'("storageBucket"\s*:\s*)"[^"]+"', r'\1"<REDACTED>"'),
        (r'("messagingSenderId"\s*:\s*)"[^"]+"', r'\1"<REDACTED>"'),
        (r'("appId"\s*:\s*)"[^"]+"', r'\1"<REDACTED>"'),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text


def lang_for(path: Path) -> str:
    if path.suffix in {".ts", ".tsx"}:
        return "typescript"
    if path.suffix == ".css":
        return "css"
    if path.suffix == ".js":
        return "javascript"
    if path.suffix == ".json":
        return "json"
    return ""


def emit_file(buf: list[str], rel: str) -> None:
    path = FRONTEND / rel
    if not path.exists():
        buf.append(f"### `{rel}`\n\nDOES NOT EXIST\n\n")
        return
    content = redact(path.read_text(encoding="utf-8"))
    lang = lang_for(path)
    buf.append(f"### `{rel}`\n\n```{lang}\n{content}```\n\n")


def emit_heading_files(buf: list[str], heading: str, files: list[str]) -> None:
    buf.append(f"## {heading}\n\n")
    for rel in files:
        emit_file(buf, rel)


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True)


def run_rg(pattern: str) -> str:
    try:
        return subprocess.check_output(
            ["rg", "-n", pattern, "frontend"],
            cwd=REPO,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        return exc.output


def main() -> None:
    buf: list[str] = []
    buf.append("# Fivvle Frontend Context\n\n")
    buf.append(
        "Generated for external UX redesign assistant. "
        "Source files are verbatim; secrets redacted.\n\n"
    )

    # 1
    buf.append("## 1. Frontend orientation\n\n")
    buf.append("### `tree -L 3 frontend` (excluding node_modules and .next)\n\n```text\n")
    tree = subprocess.check_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-ChildItem -Path frontend -Recurse -Depth 3 -Name | "
            "Where-Object { $_ -notmatch 'node_modules|\\.next' } | Sort-Object",
        ],
        cwd=REPO,
        text=True,
    )
    buf.append(tree)
    buf.append("```\n\n")
    for rel in ["package.json", "tailwind.config.ts", "next.config.js", "app/globals.css"]:
        emit_file(buf, rel)

    # 2
    section2 = [
        "app/(dashboard)/new/page.tsx",
        "components/refinement/RefineStagePanel.tsx",
        "components/chat/ChatInterface.tsx",
        "components/chat/ChatMessage.tsx",
        "components/chat/ChatInput.tsx",
        "components/chat/ChatMarkdown.tsx",
        "components/refinement/ClarifyingQuestionBlock.tsx",
        "components/refinement/ClarifyingQuestionsLoading.tsx",
        "components/refinement/RefinementThreadMessage.tsx",
        "components/refinement/PressureTestSection.tsx",
        "components/refinement/ClarityAnswerCarousel.tsx",
        "components/refinement/refinement-ascent.css",
        "components/refinement/refinement-thread.css",
        "lib/clarifying-questions.ts",
        "lib/refinement-thread.ts",
        "components/wallet/ValidationResearchPrompt.tsx",
    ]
    emit_heading_files(buf, "2. Refine flow — full surface", section2)
    buf.append("### Grep: clarifying_question | ClarifyingQuestion | refinement\n\n```text\n")
    buf.append(run_rg("clarifying_question|ClarifyingQuestion|refinement"))
    buf.append("```\n\n")

    # 3
    section3 = [
        "components/refinement/ClarifyingQuestionBlock.tsx",
        "components/refinement/ClarityAnswerCarousel.tsx",
        "lib/clarifying-questions.ts",
        "components/refinement/ClarifyingQuestionsLoading.tsx",
    ]
    emit_heading_files(buf, "3. Wizard / clarifying question rendering", section3)

    # 4
    section4 = [
        "app/(dashboard)/experiment/[id]/page.tsx",
        "components/research/ValidationReportPanel.tsx",
        "components/research/ValidationReportViewer.tsx",
        "components/research/ReportCanvas.tsx",
        "components/research/ReportScoreSection.tsx",
        "components/research/ValidationReportExportMenu.tsx",
        "components/research/report-canvas.css",
        "components/research/report-score-section.css",
        "lib/report-text.ts",
        "lib/validation-report-export.ts",
        "lib/validation-report-scores.ts",
        "lib/validation-report-score-details.ts",
    ]
    emit_heading_files(buf, "4. Report reader", section4)

    # 5
    buf.append("## 5. Shared components\n\n")
    ui_dir = FRONTEND / "components" / "ui"
    for path in sorted(ui_dir.glob("*")):
        if path.is_file():
            emit_file(buf, str(path.relative_to(FRONTEND)).replace("\\", "/"))

    # 6
    section6 = [
        "app/layout.tsx",
        "app/(dashboard)/layout.tsx",
        "app/(dashboard)/dashboard/layout.tsx",
        "app/(dashboard)/experiment/[id]/page.tsx",
        "middleware.ts",
        "lib/auth-context.tsx",
        "components/providers/AppProviders.tsx",
        "components/dashboard/ExperimentDetailPanel.tsx",
        "components/experiment/ExperimentStageNav.tsx",
        "lib/experiment-stages.ts",
        "lib/experiment-events.ts",
    ]
    emit_heading_files(buf, "6. Routing and state", section6)
    buf.append("### Grep: useExperiment | ExperimentContext\n\n```text\n")
    grep_exp = run_rg("useExperiment|ExperimentContext").strip()
    buf.append(grep_exp if grep_exp else "(no matches)")
    buf.append("\n```\n\n")

    # 7
    emit_heading_files(buf, "7. Backend API surface (frontend view)", ["lib/api.ts", "lib/types.ts"])

    # 8
    buf.append(
        """## 8. Design system status

- **Formal design system:** No Storybook, no Radix/shadcn component library. Design is a **de facto token system** in `frontend/app/globals.css` (`--fv-*` CSS variables) mapped into Tailwind via `frontend/tailwind.config.ts` (`fv.*` color keys).
- **Typography:** Inter + DM Mono via `next/font` in `app/layout.tsx`.
- **Component primitives:** Lightweight shared components under `frontend/components/ui/` (EmptyState, ErrorBanner, LoadingState, PageHeader, ToastProvider, TypeConfirmDialog) plus many utility classes in `globals.css` (`.fv-btn-primary`, `.fv-card`, `.fv-q-option`, `.fv-stage-tab`, report badges, etc.).
- **Refinement-specific styling:** `components/refinement/refinement-ascent.css` and `refinement-thread.css` layered on top of global tokens.
- **Report reader styling:** `components/research/report-canvas.css` and `report-score-section.css`.
- **Storybook / component gallery:** DOES NOT EXIST.
- **Frontend tests:**
  - `frontend/lib/__tests__/report-text.test.ts` (Vitest)
  - `frontend/vitest.config.ts`

"""
    )

    # 9
    buf.append(
        """## 9. Known frontend pain points

- **Dual report viewers:** `ValidationReportViewer.tsx` and `ReportCanvas.tsx` both render validation reports with overlapping section logic; `ExperimentDetailPanel` / stage routing may show one or the other depending on context — risk of UI drift.
- **Refinement demo vs live paths:** `components/refinement-demos/` duplicates live refinement thread components (`RefinementThreadMessage`, `PressureTestSection`) for `/refinement-demos` — styling changes must be applied in two places or demos diverge from production.
- **Clarifying question wizard state is local:** `ClarifyingQuestionBlock.tsx` owns carousel index + answers in component state; no shared hook (`useRefineChat` / `useChatThread` do not exist). `ChatInterface.tsx` is the de facto state machine (~900+ lines) mixing refine chat, research dispatch, paywall gates, and experiment lifecycle.
- **No `ExperimentContext`:** experiment state lives in `ExperimentDetailPanel.tsx` via `useState` + polling `getExperiment()`; child stage panels receive props/callbacks rather than a shared context — similar data refetched in multiple tabs.
- **API types monolith:** `lib/types.ts` holds refinement, research, landing, wallet, and chat types in one large file; frontend rendering assumptions can drift from backend schema without compile-time coupling on nested report fields.
- **Loading states uneven:** `ClarifyingQuestionsLoading.tsx` covers pending clarify turns; report reader loading is split between `ValidationReportPanel.tsx` polling and inline spinners in `ReportCanvas.tsx` — no unified skeleton for full report load.
- **Research dispatch split:** auto-dispatch after finalize in `ChatInterface.tsx` plus manual `confirmExperiment()` in `ExperimentDetailPanel.tsx` / `ValidationResearchPrompt.tsx` — two entry points to start research.
- **Legacy CSS aliases:** `globals.css` duplicates clarifying-option styles (`.fv-q-option` vs `.q-option`) and message bubbles (`.fv-msg-*` vs `.msg-bubble-*`) suggesting incremental redesign without cleanup.
- **Uncommitted report export work:** `ValidationReportExportMenu.tsx` is new/untracked; `validation-report-export.ts` and `report-text.ts` have large in-progress diffs — export markdown path may not match rendered report sections yet.

"""
    )

    # 10
    buf.append("## 10. Recent uncommitted frontend work\n\n")
    buf.append("### `git status -- frontend`\n\n```text\n")
    buf.append(run_git(["status", "--", "frontend"]))
    buf.append("```\n\n")
    buf.append("### `git diff HEAD --stat -- frontend`\n\n```text\n")
    buf.append(run_git(["diff", "HEAD", "--stat", "--", "frontend"]))
    buf.append("```\n\n")
    diff_text = run_git(["diff", "HEAD", "--", "frontend"])
    diff_line_count = len(diff_text.splitlines())
    if diff_line_count <= 500:
        buf.append("### `git diff HEAD -- frontend`\n\n```diff\n")
        buf.append(diff_text)
        buf.append("```\n")
    else:
        buf.append(
            f"### `git diff HEAD -- frontend` ({diff_line_count} lines — exceeds 500; omitted)\n\n"
        )
        buf.append(
            "Diff is too large to inline. Run `git diff HEAD -- frontend` locally for full patch.\n"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(buf)
    OUT.write_text(text, encoding="utf-8")
    line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
    print(f"Wrote {OUT} ({line_count} lines)")


if __name__ == "__main__":
    main()
