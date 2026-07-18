"use client";

import { useEffect, useState, type FormEvent } from "react";
import { EditableCopy } from "@/components/landing-templates/EditableCopy";

type Props = {
  value: string;
  onSave: (next: string) => void;
  /** Soft display cap for the character counter (warn at 90%). */
  softCap: number;
  /** Schema hard cap — blocks save when exceeded. */
  hardCap: number;
  disabled?: boolean;
  saving?: boolean;
  className?: string;
  /** Min height hint for the editable surface. */
  minRows?: number;
};

/**
 * Brutalist chrome around EditableCopy: blur-commit, Escape-revert, multiline.
 * Character count lives below the wrapper (not inside EditableCopy).
 * Soft-cap overflow warns in red but still saves; hardCap blocks save.
 */
export function BrutalistEditableField({
  value,
  onSave,
  softCap,
  hardCap,
  disabled = false,
  saving = false,
  className = "",
  minRows = 3,
}: Props) {
  const [len, setLen] = useState(value.length);
  const [remountKey, setRemountKey] = useState(0);

  useEffect(() => {
    setLen(value.length);
  }, [value]);

  function handleInput(e: FormEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (!target.isContentEditable) return;
    const text = (target.innerText ?? "").replace(/\u00a0/g, " ");
    setLen(text.length);
  }

  function handleChange(next: string) {
    setLen(next.length);
    if (next.length === 0 || next.length > hardCap) {
      // Reject empty / over-schema; remount to restore server truth in the DOM.
      setRemountKey((k) => k + 1);
      setLen(value.length);
      return;
    }
    if (next === value) return;
    onSave(next);
  }

  const warnAt = Math.floor(softCap * 0.9);
  const counterClass =
    len > softCap || len > hardCap
      ? "text-status-critical"
      : len >= softCap || len >= warnAt
        ? "text-brand-primary"
        : "text-ink-primary/40";

  const locked = disabled || saving;

  return (
    <div className={className}>
      <div
        onInput={handleInput}
        className="border-2 border-border-master bg-white p-3 shadow-brutal-md focus-within:border-brand-primary"
      >
        <EditableCopy
          key={remountKey}
          value={value}
          onChange={handleChange}
          editable={!locked}
          multiline
          as="div"
          className="min-h-[4.5rem] w-full font-mono text-body-sm text-ink-primary outline-none"
          style={{ minHeight: `${minRows * 1.5}rem` }}
        />
      </div>
      <div className="mt-1 flex items-center justify-between">
        <span className="font-mono text-mono-sm uppercase text-ink-primary/40">
          {saving ? "Saving…" : "\u00a0"}
        </span>
        <span className={`font-mono text-mono-sm ${counterClass}`}>
          {len} / {softCap}
        </span>
      </div>
    </div>
  );
}
