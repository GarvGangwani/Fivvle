"use client";

import { useState } from "react";
import { SAMPLE_REFINED } from "./shared";

const SLOTS = [
  { id: "oneLiner", label: "One-liner", key: "oneLiner" as const },
  { id: "audience", label: "Who hurts", key: "audience" as const },
  { id: "value", label: "Outcome", key: "value" as const },
  { id: "risk", label: "Biggest risk", key: "risk" as const },
  { id: "test", label: "How we test", key: "test" as const },
];

export function BlueprintBuilderDemo() {
  const [filled, setFilled] = useState(0);
  const [input, setInput] = useState("");

  function fillNext() {
    if (filled >= SLOTS.length) return;
    setFilled((n) => n + 1);
    setInput("");
  }

  return (
    <div className="rd-demo">
      <p className="rd-demo-label">Concept 3</p>
      <h2 className="rd-demo-title">Blueprint Builder</h2>
      <p className="rd-demo-desc">
        A live hypothesis blueprint fills as you answer — history is a build log,
        not a chat thread.
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rd-panel">
          <p className="mb-2 text-sm font-semibold text-[var(--fv-text)]">
            {filled < SLOTS.length
              ? `Fill: ${SLOTS[filled].label}`
              : "Blueprint complete"}
          </p>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              filled < SLOTS.length
                ? `Describe ${SLOTS[filled].label.toLowerCase()}…`
                : "Done"
            }
            disabled={filled >= SLOTS.length}
            className="fv-input mb-3 min-h-[100px] w-full resize-y text-sm"
          />
          <button
            type="button"
            className="rd-btn-primary"
            disabled={filled >= SLOTS.length || !input.trim()}
            onClick={fillNext}
          >
            Add to blueprint
          </button>

          {filled > 0 && (
            <div className="mt-4 border-t border-[var(--fv-border)] pt-3">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-[var(--fv-text-muted)]">
                Build log
              </p>
              <ul className="space-y-1 text-xs text-[var(--fv-text-soft)]">
                {SLOTS.slice(0, filled).map((slot) => (
                  <li key={slot.id}>
                    ✓ {slot.label} added
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="rd-panel border-dashed">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-[var(--fv-accent)]">
            Idea Blueprint
          </p>
          <div className="space-y-3">
            {SLOTS.map((slot, index) => {
              const isFilled = index < filled;
              const value = isFilled ? SAMPLE_REFINED[slot.key] : null;
              return (
                <div
                  key={slot.id}
                  className={`rounded-lg border p-3 transition-all ${
                    isFilled
                      ? "border-[var(--fv-border-strong)] bg-[var(--fv-surface-2)]"
                      : "border-dashed border-[var(--fv-border)] opacity-50"
                  }`}
                >
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--fv-text-muted)]">
                    {slot.label}
                  </p>
                  <p className="mt-1 text-sm text-[var(--fv-text)]">
                    {value ?? "—"}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
