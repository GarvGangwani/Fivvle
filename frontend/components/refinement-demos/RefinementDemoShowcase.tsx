"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { DEMO_CONCEPTS } from "./shared";
import { RefinementAscentDemo } from "./RefinementAscentDemo";
import { RefinementPeakDemo } from "./RefinementPeakDemo";
import { QuestMapDemo } from "./QuestMapDemo";
import { IdeaStatsDemo } from "./IdeaStatsDemo";
import { BlueprintBuilderDemo } from "./BlueprintBuilderDemo";
import { CardDraftDemo } from "./CardDraftDemo";
import { PitchDeckDemo } from "./PitchDeckDemo";
import { EvidenceBoardDemo } from "./EvidenceBoardDemo";
import { ConfidenceDuelDemo } from "./ConfidenceDuelDemo";
import "./refinement-demos.css";

const DEMOS: Record<string, () => React.ReactNode> = {
  "refinement-peak": () => <RefinementPeakDemo />,
  "refinement-ascent": () => <RefinementAscentDemo />,
  "quest-map": () => <QuestMapDemo />,
  "idea-stats": () => <IdeaStatsDemo />,
  blueprint: () => <BlueprintBuilderDemo />,
  "card-draft": () => <CardDraftDemo />,
  "pitch-deck": () => <PitchDeckDemo />,
  "evidence-board": () => <EvidenceBoardDemo />,
  "confidence-duel": () => <ConfidenceDuelDemo />,
};

export function RefinementDemoShowcase() {
  const [activeId, setActiveId] = useState("refinement-ascent");
  const DemoView = DEMOS[activeId];

  return (
    <div className="rd-showcase">
      <header className="rd-showcase-header">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link
              href="/"
              className="mb-2 inline-flex items-center gap-1.5 text-xs font-medium text-[var(--fv-text-muted)] no-underline hover:text-[var(--fv-text)]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to app
            </Link>
            <h1 className="text-lg font-bold tracking-tight text-[var(--fv-text)]">
              Refinement UI concepts
            </h1>
            <p className="mt-0.5 text-sm text-[var(--fv-text-muted)]">
              Interactive mockups — click through each pattern. Sample idea:
              psychology-based dating app.
            </p>
          </div>
          <span className="rounded-full border border-[var(--fv-border)] bg-[var(--fv-surface)] px-3 py-1 text-[11px] font-semibold text-[var(--fv-text-muted)]">
            Preview only · not wired to backend
          </span>
        </div>
      </header>

      <div className="rd-showcase-body">
        <nav className="rd-nav" aria-label="Refinement concepts">
          {DEMO_CONCEPTS.map((concept) => (
            <button
              key={concept.id}
              type="button"
              onClick={() => setActiveId(concept.id)}
              className={`rd-nav-item ${
                activeId === concept.id ? "rd-nav-item-active" : ""
              }`}
            >
              <div className="rd-nav-title">{concept.title}</div>
              <div className="rd-nav-sub">{concept.subtitle}</div>
            </button>
          ))}
        </nav>

        <main
          className={`rd-stage ${activeId === "quest-map" ? "rd-stage--wide" : ""}`}
          key={activeId}
        >
          {DemoView?.()}
        </main>
      </div>
    </div>
  );
}
