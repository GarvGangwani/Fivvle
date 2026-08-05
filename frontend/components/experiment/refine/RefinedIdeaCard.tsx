"use client";

import { useState } from "react";
import type { RefinedIdea } from "@/lib/types";

type Props = {
  refinedIdea: RefinedIdea | string;
  isFinalized: boolean;
  isJustUpdated?: boolean;
  wipDiffers?: boolean;
};

export function RefinedIdeaCard({
  refinedIdea,
  isFinalized,
  isJustUpdated = false,
  wipDiffers = false,
}: Props) {
  const [copied, setCopied] = useState(false);

  const structuredIdea = typeof refinedIdea === "string" ? null : refinedIdea;
  const displayText =
    structuredIdea?.refined_one_liner ??
    (typeof refinedIdea === "string" ? refinedIdea : "");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displayText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  return (
    <div
      className={`relative rounded-lg border-2 shadow-brutal-lg transition-all ${
        isFinalized && !wipDiffers
          ? "border-status-success bg-status-success/10 fv-brutal-hover"
          : "border-accent bg-accent text-ink-inverse fv-brutal-hover-glow"
      } ${isJustUpdated ? "ring-2 ring-brutalist-yellow ring-offset-2" : ""}`}
    >
      <div className="absolute -top-3 -right-3 z-10">
        {isFinalized && !wipDiffers ? (
          <div className="rounded-sm bg-status-success text-ink-inverse px-3 py-1 border-2 border-border-master shadow-brutal-sm font-mono text-mono-sm uppercase font-bold flex items-center gap-1">
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 14 }}
              aria-hidden="true"
            >
              check_circle
            </span>
            FINALIZED
          </div>
        ) : (
          <div className="rounded-sm bg-brutalist-yellow text-ink-primary px-3 py-1 border-2 border-border-master shadow-brutal-sm font-mono text-mono-sm uppercase font-bold">
            {wipDiffers ? "UPDATED WIP" : "WIP"}
          </div>
        )}
      </div>

      <div className="p-5">
        <div className="mb-4">
          <p
            className={`font-mono text-mono-sm uppercase mb-2 ${
              isFinalized && !wipDiffers
                ? "text-status-success"
                : "text-brutalist-yellow"
            }`}
          >
            THE REFINED IDEA
          </p>
          <p
            className={`font-headline text-headline-md leading-tight ${
              isFinalized && !wipDiffers ? "text-ink-primary" : "text-ink-inverse"
            }`}
          >
            {displayText}
          </p>
        </div>

        {structuredIdea ? (
          <div
            className={`space-y-3 pt-4 border-t-2 ${
              isFinalized && !wipDiffers
                ? "border-status-success/30"
                : "border-ink-inverse/20"
            }`}
          >
            {structuredIdea.target_audience ? (
              <StructuredField
                label="TARGET AUDIENCE"
                value={structuredIdea.target_audience}
                inverted={!(isFinalized && !wipDiffers)}
              />
            ) : null}
            {structuredIdea.value_proposition ? (
              <StructuredField
                label="VALUE PROPOSITION"
                value={structuredIdea.value_proposition}
                inverted={!(isFinalized && !wipDiffers)}
              />
            ) : null}
            {structuredIdea.risks && structuredIdea.risks.length > 0 ? (
              <div>
                <p
                  className={`font-mono text-mono-sm uppercase mb-1 ${
                    isFinalized && !wipDiffers
                      ? "text-ink-tertiary"
                      : "text-ink-inverse/60"
                  }`}
                >
                  KEY RISKS
                </p>
                <ul
                  className={`space-y-1 ${
                    isFinalized && !wipDiffers
                      ? "text-ink-primary"
                      : "text-ink-inverse"
                  }`}
                >
                  {structuredIdea.risks.map((risk, i) => (
                    <li key={i} className="font-body text-body-sm flex gap-2">
                      <span
                        className={
                          isFinalized && !wipDiffers
                            ? "text-status-critical"
                            : "text-brutalist-yellow"
                        }
                      >
                        →
                      </span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        <button
          type="button"
          onClick={() => void handleCopy()}
          className={`mt-4 w-full border-2 py-2 px-3 font-label-md text-label-md uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
            isFinalized && !wipDiffers
              ? "border-status-success bg-transparent text-ink-primary hover:bg-status-success/20"
              : "border-ink-inverse bg-transparent text-ink-inverse hover:bg-ink-inverse/10"
          }`}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 16 }}
            aria-hidden="true"
          >
            {copied ? "check" : "content_copy"}
          </span>
          {copied ? "COPIED" : "COPY IDEA"}
        </button>
      </div>
    </div>
  );
}

function StructuredField({
  label,
  value,
  inverted,
}: {
  label: string;
  value: string;
  inverted: boolean;
}) {
  return (
    <div>
      <p
        className={`font-mono text-mono-sm uppercase mb-1 ${
          inverted ? "text-ink-inverse/60" : "text-ink-tertiary"
        }`}
      >
        {label}
      </p>
      <p
        className={`font-body text-body-sm ${
          inverted ? "text-ink-inverse" : "text-ink-primary"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
