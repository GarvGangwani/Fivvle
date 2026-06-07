"use client";

interface RegenerateButtonProps {
  sectionType: string;
  label?: string;
  onRegenerate: (sectionType: string) => void;
  isLoading?: boolean;
}

export function RegenerateButton({
  sectionType,
  label,
  onRegenerate,
  isLoading = false,
}: RegenerateButtonProps) {
  return (
    <button
      type="button"
      disabled={isLoading}
      onClick={() => onRegenerate(sectionType)}
      className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent-muted)] hover:text-white disabled:opacity-50"
    >
      {isLoading ? "Regenerating…" : label ?? `Regenerate ${sectionType}`}
    </button>
  );
}
