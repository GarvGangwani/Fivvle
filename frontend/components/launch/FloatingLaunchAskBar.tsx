"use client";

/**
 * Presentational-only launch ask bar. Not wired to a backend in this PR —
 * a scoped launch-context chat is a future PR.
 */
export function FloatingLaunchAskBar() {
  return (
    <div className="flex items-center gap-3 border-2 border-border-master bg-surface-card px-4 py-3 shadow-brutal-md">
      <span
        className="material-symbols-outlined shrink-0 text-brand-primary"
        style={{ fontVariationSettings: "'FILL' 1" }}
        aria-hidden="true"
      >
        auto_awesome
      </span>
      <input
        type="text"
        readOnly
        placeholder="Ask about your launch..."
        aria-label="Ask about your launch"
        className="min-w-0 flex-1 bg-transparent text-body-md italic text-ink-primary placeholder:italic placeholder:text-ink-tertiary focus:outline-none"
      />
      <button
        type="button"
        className="shrink-0 bg-ink-primary px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-ink-inverse"
      >
        Ask
      </button>
    </div>
  );
}
