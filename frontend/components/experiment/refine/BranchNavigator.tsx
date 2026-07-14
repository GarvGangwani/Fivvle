"use client";

type Props = {
  currentIndex: number;
  totalCount: number;
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  isNavigating: boolean;
};

export function BranchNavigator({
  currentIndex,
  totalCount,
  canNavigatePrev,
  canNavigateNext,
  onPrev,
  onNext,
  isNavigating,
}: Props) {
  if (totalCount <= 1) return null;

  return (
    <div className="inline-flex items-center gap-1 border border-border-master bg-surface-elevated px-2 py-1">
      <button
        type="button"
        onClick={onPrev}
        disabled={!canNavigatePrev || isNavigating}
        aria-label="Previous version"
        className="disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-card p-0.5 transition-colors"
      >
        <span
          className="material-symbols-outlined text-ink-secondary"
          style={{ fontSize: 14 }}
          aria-hidden="true"
        >
          chevron_left
        </span>
      </button>
      <span className="font-mono text-mono-sm text-ink-secondary tabular-nums px-1 min-w-[40px] text-center">
        {isNavigating ? "..." : `${currentIndex + 1} / ${totalCount}`}
      </span>
      <button
        type="button"
        onClick={onNext}
        disabled={!canNavigateNext || isNavigating}
        aria-label="Next version"
        className="disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-card p-0.5 transition-colors"
      >
        <span
          className="material-symbols-outlined text-ink-secondary"
          style={{ fontSize: 14 }}
          aria-hidden="true"
        >
          chevron_right
        </span>
      </button>
    </div>
  );
}
