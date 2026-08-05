import {
  mapStatusToPill,
  type PillState,
} from "@/components/dashboard/dashboard-helpers";

const PILL_STYLES: Record<
  PillState,
  { container: string; dot: string; pulse: boolean }
> = {
  SPARK: {
    container: "bg-surface-elevated text-ink-secondary",
    dot: "bg-ink-tertiary",
    pulse: false,
  },
  REFINING: {
    container: "bg-brand-primary-soft text-brand-primary-deep",
    dot: "bg-accent",
    pulse: true,
  },
  RESEARCHING: {
    container: "bg-accent text-ink-inverse",
    dot: "bg-ink-inverse",
    pulse: true,
  },
  LAUNCHED: {
    container: "bg-brutalist-yellow text-ink-primary",
    dot: "bg-ink-primary",
    pulse: false,
  },
  COMPLETE: {
    container: "bg-status-success text-ink-inverse",
    dot: "bg-ink-inverse",
    pulse: false,
  },
  CRITICAL: {
    container: "bg-status-critical text-ink-inverse",
    dot: "bg-ink-inverse",
    pulse: true,
  },
  ARCHIVED: {
    container: "bg-canvas-bg text-ink-tertiary",
    dot: "bg-ink-tertiary",
    pulse: false,
  },
};

interface StatusBadgeProps {
  status: string;
  /** Force pill state (e.g. archived view always ARCHIVED). */
  forcePill?: PillState;
}

export function StatusBadge({ status, forcePill }: StatusBadgeProps) {
  const pill = forcePill ?? mapStatusToPill(status);
  const styles = PILL_STYLES[pill];

  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-sm border-2 border-border-master px-2 py-1 font-label-md text-label-md uppercase ${styles.container}`}
    >
      <span
        className={`h-2 w-2 shrink-0 rounded-full ${styles.dot} ${
          styles.pulse ? "animate-pulse motion-reduce:animate-none" : ""
        }`}
        aria-hidden
      />
      {pill}
    </span>
  );
}
