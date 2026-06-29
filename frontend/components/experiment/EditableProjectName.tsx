"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2, Pencil } from "lucide-react";
import { renameExperiment, ApiError } from "@/lib/api";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { notifyExperimentsChanged } from "@/lib/experiment-events";

interface EditableProjectNameProps {
  experimentId: string;
  name: string | null | undefined;
  rawIdea: string;
  onRenamed?: (name: string) => void;
  /** Use compact styling for inline headers. */
  variant?: "header" | "inline";
  className?: string;
}

export function EditableProjectName({
  experimentId,
  name,
  rawIdea,
  onRenamed,
  variant = "header",
  className = "",
}: EditableProjectNameProps) {
  const displayName = getExperimentDisplayName({ name, raw_idea: rawIdea });
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(displayName);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) {
      setDraft(getExperimentDisplayName({ name, raw_idea: rawIdea }));
    }
  }, [name, rawIdea, editing]);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const cancel = useCallback(() => {
    setEditing(false);
    setDraft(displayName);
    setError(null);
  }, [displayName]);

  const save = useCallback(async () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      setError("Name cannot be empty.");
      return;
    }
    if (trimmed === (name?.trim() || displayName)) {
      setEditing(false);
      setError(null);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await renameExperiment(experimentId, trimmed);
      onRenamed?.(updated.name?.trim() || trimmed);
      notifyExperimentsChanged();
      setEditing(false);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 400
          ? "Please enter a valid project name."
          : "Could not save name. Try again.",
      );
    } finally {
      setSaving(false);
    }
  }, [draft, displayName, experimentId, name, onRenamed]);

  const titleClass =
    variant === "header"
      ? "text-xl font-semibold tracking-[-0.02em] text-[var(--fv-text)] sm:text-2xl"
      : "text-[15px] font-semibold text-[var(--fv-text)]";

  if (editing) {
    return (
      <div className={`min-w-0 ${className}`}>
        <div className="flex min-w-0 items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={draft}
            maxLength={100}
            disabled={saving}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void save();
              if (e.key === "Escape") cancel();
            }}
            className="fv-input min-w-0 flex-1 px-3 py-1.5 text-sm sm:text-base"
            aria-label="Project name"
          />
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving}
            className="fv-btn-primary shrink-0 px-2.5 py-1.5"
            aria-label="Save project name"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
          </button>
        </div>
        {error && (
          <p className="mt-1 text-xs text-[var(--fv-danger)]" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className={`group flex min-w-0 items-center gap-2 ${className}`}>
      <h1 className={`min-w-0 truncate ${titleClass}`}>{displayName}</h1>
      <button
        type="button"
        onClick={() => setEditing(true)}
        className="fv-icon-btn shrink-0 opacity-60 transition-opacity group-hover:opacity-100"
        aria-label="Rename project"
        title="Rename project"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
