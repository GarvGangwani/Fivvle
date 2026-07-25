"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { createExperiment } from "@/lib/api";

export default function NewExperimentPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canCreate = name.trim().length >= 3 && !creating;

  const handleCreate = useCallback(async () => {
    if (!canCreate) return;
    setCreating(true);
    setError(null);
    try {
      const experiment = await createExperiment(name.trim());
      router.push(`/experiment/${experiment.id}`);
    } catch {
      setError("Could not create project. Try again.");
      setCreating(false);
    }
  }, [canCreate, name, router]);

  return (
    <div className="mx-auto max-w-2xl px-gutter pb-16 pt-24">
      <div className="mb-2 font-label-md uppercase text-brand-primary">
        NEW VALIDATION
      </div>
      <h1 className="mb-4 font-display text-display-lg uppercase">
        What are you calling it?
      </h1>
      <p className="mb-8 font-body text-body-lg text-ink-secondary">
        Give your validation a short name. You&apos;ll fill in the idea, files,
        and everything else on the canvas.
      </p>

      <div className="space-y-6 rounded-lg border-2 border-border-master bg-surface-card p-8 shadow-brutal-md">
        <div>
          <label className="mb-2 block font-label-md text-label-md uppercase">
            PROJECT NAME
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleCreate();
            }}
            placeholder="e.g. Async standup bot for remote teams"
            maxLength={120}
            autoFocus
            className="w-full rounded-md border-2 border-border-master bg-surface-card px-4 py-3 font-body text-body-lg focus:outline-none focus:shadow-brutal-primary"
          />
          <p className="mt-2 font-mono text-mono-sm text-ink-tertiary">
            {name.length}/120 CHARACTERS
          </p>
        </div>

        {error ? (
          <p className="font-body text-body-sm text-status-critical">{error}</p>
        ) : null}

        <button
          type="button"
          onClick={() => void handleCreate()}
          disabled={!canCreate}
          className="w-full rounded-sm border-2 border-border-master bg-brand-primary px-8 py-4 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-md transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-lg active:translate-x-0 active:translate-y-0 active:shadow-none disabled:cursor-not-allowed disabled:opacity-50"
        >
          {creating ? "CREATING..." : "PROCEED TO CANVAS →"}
        </button>
      </div>
    </div>
  );
}
