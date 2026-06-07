"use client";

import { PAGE_GOALS, type PageGoal } from "@/lib/types";
import { ThemePicker } from "./ThemePicker";
import type { TemplateId } from "@/lib/templates";

interface GoalSelectorProps {
  selected: PageGoal;
  templateId: TemplateId;
  onSelect: (goal: PageGoal) => void;
  onTemplateSelect: (id: TemplateId) => void;
  onBack: () => void;
  onAnalyze: () => void;
  isSubmitting: boolean;
}

export function GoalSelector({
  selected,
  templateId,
  onSelect,
  onTemplateSelect,
  onBack,
  onAnalyze,
  isSubmitting,
}: GoalSelectorProps) {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-8">
      <div className="space-y-2 text-center">
        <h2 className="text-3xl font-semibold tracking-tight text-white">
          Choose your page goal
        </h2>
        <p className="text-zinc-400">
          The strategist adapts section order, CTA style, and copy framework to
          your conversion objective.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PAGE_GOALS.map((goal) => {
          const active = selected === goal.id;
          return (
            <button
              key={goal.id}
              type="button"
              onClick={() => onSelect(goal.id)}
              className={`rounded-2xl border p-5 text-left transition-all ${
                active
                  ? "fv-card-selected border-[var(--fv-accent)]"
                  : "fv-card fv-card-hover border-white/10"
              }`}
            >
              <span
                className={`text-xs font-semibold uppercase tracking-wider ${
                  active ? "text-[var(--fv-accent)]" : "text-[var(--fv-text-muted)]"
                }`}
              >
                {goal.id.replace(/_/g, " ")}
              </span>
              <h3 className="mt-2 text-lg font-semibold text-white">
                {goal.label}
              </h3>
              <p className="mt-1 text-sm text-zinc-400">{goal.description}</p>
            </button>
          );
        })}
      </div>

      <ThemePicker
        selected={templateId}
        onSelect={onTemplateSelect}
        disabled={isSubmitting}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={isSubmitting}
          className="fv-btn-ghost px-6 py-3 disabled:opacity-50"
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={onAnalyze}
          disabled={isSubmitting}
          className="fv-btn-primary px-8 py-3 disabled:opacity-50"
        >
          {isSubmitting ? "Starting analysis…" : "Analyze & generate →"}
        </button>
      </div>
    </div>
  );
}
