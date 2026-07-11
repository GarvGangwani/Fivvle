"use client";

import type { RefinedIdea } from "@/lib/types";

type Props = {
  refinedIdea: RefinedIdea | string;
  isFinalized: boolean;
};

export function RefinedIdeaCard({ refinedIdea, isFinalized }: Props) {
  const borderClass = isFinalized
    ? "border-status-success"
    : "border-brand-primary";

  if (typeof refinedIdea === "string") {
    return (
      <div
        className={`border-2 p-4 bg-surface-card ${borderClass} shadow-brutal-md`}
      >
        <RefinedIdeaField label="ONE-LINER" value={refinedIdea} />
      </div>
    );
  }

  return (
    <div
      className={`border-2 p-4 bg-surface-card ${borderClass} shadow-brutal-md`}
    >
      {refinedIdea.project_name ? (
        <RefinedIdeaField label="PROJECT NAME" value={refinedIdea.project_name} />
      ) : null}
      {refinedIdea.refined_one_liner ? (
        <RefinedIdeaField
          label="ONE-LINER"
          value={refinedIdea.refined_one_liner}
        />
      ) : null}
      {refinedIdea.target_audience ? (
        <RefinedIdeaField
          label="TARGET AUDIENCE"
          value={refinedIdea.target_audience}
        />
      ) : null}
      {refinedIdea.value_proposition ? (
        <RefinedIdeaField
          label="VALUE PROPOSITION"
          value={refinedIdea.value_proposition}
        />
      ) : null}
      {refinedIdea.risks && refinedIdea.risks.length > 0 ? (
        <div className="mb-3">
          <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-1">
            RISKS
          </div>
          <ul className="space-y-1">
            {refinedIdea.risks.map((risk, i) => (
              <li key={i} className="font-body text-body-sm flex gap-2">
                <span className="text-brand-primary">→</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {refinedIdea.headline ? (
        <RefinedIdeaField label="HEADLINE" value={refinedIdea.headline} />
      ) : null}
      {refinedIdea.subheadline ? (
        <RefinedIdeaField label="SUBHEADLINE" value={refinedIdea.subheadline} />
      ) : null}
      {refinedIdea.cta_text ? (
        <RefinedIdeaField label="CTA" value={refinedIdea.cta_text} />
      ) : null}
    </div>
  );
}

function RefinedIdeaField({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-3 last:mb-0">
      <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-1">
        {label}
      </div>
      <p className="font-body text-body-sm">{value}</p>
    </div>
  );
}
