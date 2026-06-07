"use client";

import type { CopyJson } from "@/lib/types";

interface CopyFieldsEditorProps {
  copy: CopyJson;
  onChange: (copy: CopyJson) => void;
  disabled?: boolean;
}

export function CopyFieldsEditor({
  copy,
  onChange,
  disabled,
}: CopyFieldsEditorProps) {
  const hero = copy.hero ?? {
    headline: "",
    subheadline: "",
    cta: "",
  };

  function updateHero(field: keyof typeof hero, value: string) {
    onChange({
      ...copy,
      hero: { ...hero, [field]: value },
    });
  }

  const problem = copy.problem ?? { heading: "", body: "" };
  const cta = copy.cta ?? { heading: "", subheading: "", button: "" };

  return (
    <div className="space-y-4">
      <p className="fv-panel-label">Page copy</p>

      <label className="block space-y-1.5">
        <span className="text-xs text-[var(--fv-text-muted)]">Hero headline</span>
        <input
          type="text"
          disabled={disabled}
          value={hero.headline}
          onChange={(e) => updateHero("headline", e.target.value)}
          className="fv-input px-3 py-2 text-sm"
        />
      </label>

      <label className="block space-y-1.5">
        <span className="text-xs text-[var(--fv-text-muted)]">Hero subheadline</span>
        <textarea
          disabled={disabled}
          rows={3}
          value={hero.subheadline}
          onChange={(e) => updateHero("subheadline", e.target.value)}
          className="fv-input resize-none px-3 py-2 text-sm"
        />
      </label>

      <label className="block space-y-1.5">
        <span className="text-xs text-[var(--fv-text-muted)]">Hero CTA button</span>
        <input
          type="text"
          disabled={disabled}
          value={hero.cta}
          onChange={(e) => updateHero("cta", e.target.value)}
          className="fv-input px-3 py-2 text-sm"
        />
      </label>

      {problem.heading && (
        <label className="block space-y-1.5">
          <span className="text-xs text-[var(--fv-text-muted)]">Problem heading</span>
          <input
            type="text"
            disabled={disabled}
            value={problem.heading}
            onChange={(e) =>
              onChange({
                ...copy,
                problem: { ...problem, heading: e.target.value },
              })
            }
            className="fv-input px-3 py-2 text-sm"
          />
        </label>
      )}

      {cta.heading && (
        <label className="block space-y-1.5">
          <span className="text-xs text-[var(--fv-text-muted)]">CTA section heading</span>
          <input
            type="text"
            disabled={disabled}
            value={cta.heading}
            onChange={(e) =>
              onChange({
                ...copy,
                cta: { ...cta, heading: e.target.value },
              })
            }
            className="fv-input px-3 py-2 text-sm"
          />
        </label>
      )}
    </div>
  );
}
