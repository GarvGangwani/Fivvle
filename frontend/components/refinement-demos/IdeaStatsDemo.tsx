"use client";

import { useState } from "react";
import { SAMPLE_PITCH } from "./shared";

interface Stat {
  id: string;
  label: string;
  value: number;
  hint: string;
}

const INITIAL_STATS: Stat[] = [
  { id: "clarity", label: "Clarity", value: 18, hint: "Can a stranger get it in one sentence?" },
  { id: "audience", label: "Audience", value: 12, hint: "How specific is the who?" },
  { id: "edge", label: "Differentiation", value: 8, hint: "Why not existing apps?" },
  { id: "test", label: "Testability", value: 22, hint: "Can we validate with a landing page?" },
];

const BOOSTS: Record<string, number> = {
  clarity: 28,
  audience: 35,
  edge: 30,
  test: 18,
};

export function IdeaStatsDemo() {
  const [stats, setStats] = useState(INITIAL_STATS);
  const [step, setStep] = useState(0);
  const [pulseId, setPulseId] = useState<string | null>(null);

  const prompts = [
    { statId: "clarity", question: "Tighten your one-liner in one sentence." },
    { statId: "audience", question: "Who is the first user you’d manually recruit?" },
    { statId: "edge", question: "What do swipe apps fail to deliver that you do?" },
  ];

  function boostStat(statId: string) {
    setStats((prev) =>
      prev.map((s) =>
        s.id === statId
          ? { ...s, value: Math.min(100, s.value + (BOOSTS[statId] ?? 20)) }
          : s,
      ),
    );
    setPulseId(statId);
    window.setTimeout(() => setPulseId(null), 600);
    setStep((s) => Math.min(s + 1, prompts.length));
  }

  const ready = stats.every((s) => s.value >= 60);

  return (
    <div className="rd-demo">
      <p className="rd-demo-label">Concept 2</p>
      <h2 className="rd-demo-title">Idea Stats</h2>
      <p className="rd-demo-desc">
        RPG-style meters rise as answers get sharper. Research unlocks when all
        stats cross the threshold.
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="rd-panel">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--fv-text-muted)]">
            Your pitch
          </p>
          <p className="mb-4 text-sm leading-relaxed text-[var(--fv-text-soft)]">
            {SAMPLE_PITCH}
          </p>

          {step < prompts.length ? (
            <>
              <p className="mb-3 text-sm font-medium text-[var(--fv-text)]">
                {prompts[step].question}
              </p>
              <textarea
                className="fv-input mb-3 min-h-[88px] w-full resize-y text-sm"
                placeholder="Short answer…"
              />
              <button
                type="button"
                className="rd-btn-primary"
                onClick={() => boostStat(prompts[step].statId)}
              >
                Submit answer (+{BOOSTS[prompts[step].statId]} {prompts[step].statId})
              </button>
            </>
          ) : (
            <div className="rounded-xl border border-[var(--fv-success)]/30 bg-[color-mix(in_srgb,var(--fv-success)_10%,transparent)] p-4">
              <p className="text-sm font-semibold text-[var(--fv-success)]">
                Stats threshold reached
              </p>
              <p className="mt-1 text-xs text-[var(--fv-text-muted)]">
                Hypothesis is testable — ready to run research.
              </p>
            </div>
          )}
        </div>

        <div className="space-y-3">
          {stats.map((stat) => (
            <div
              key={stat.id}
              className={`rd-panel !p-3 transition-transform ${
                pulseId === stat.id ? "scale-[1.02]" : ""
              }`}
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wide text-[var(--fv-text-soft)]">
                  {stat.label}
                </span>
                <span className="text-sm font-bold text-[var(--fv-accent)]">
                  {stat.value}
                </span>
              </div>
              <div className="rd-progress-track">
                <div
                  className="rd-progress-fill"
                  style={{ width: `${stat.value}%` }}
                />
              </div>
              <p className="mt-1.5 text-[10px] text-[var(--fv-text-muted)]">
                {stat.hint}
              </p>
            </div>
          ))}
          <button
            type="button"
            className={`rd-btn w-full ${ready ? "rd-btn-primary" : ""}`}
            disabled={!ready}
          >
            Validate idea
          </button>
        </div>
      </div>
    </div>
  );
}
