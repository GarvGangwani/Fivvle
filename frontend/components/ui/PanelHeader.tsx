import type { ReactNode } from "react";

export type PanelHeaderProps = {
  variant?: "default" | "minimal";
  /** Small uppercase label above the title (e.g. "Phase 05 · Signal"). */
  phaseLabel?: string;
  title?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  breadcrumb?: ReactNode;
  /** Sticky within the nearest scroll container. Default false. */
  sticky?: boolean;
  className?: string;
};

/**
 * Shared act/panel chrome. Brutalist: 2px bottom border, no radius, no shadow.
 * Typography helpers (`font-mono` / `font-headline`) are inlined — candidate
 * extraction for a future primitives PR.
 */
export function PanelHeader({
  variant = "default",
  phaseLabel,
  title,
  badge,
  actions,
  breadcrumb,
  sticky = false,
  className = "",
}: PanelHeaderProps) {
  const stickyClass = sticky ? "sticky top-0 z-10" : "";
  const hasRight = Boolean(badge || actions);

  if (variant === "minimal") {
    const showContent = Boolean(breadcrumb || actions || badge);
    if (!showContent) {
      return (
        <div
          role="presentation"
          aria-hidden="true"
          className={`h-0 shrink-0 border-b-[1px] border-border-master ${stickyClass} ${className}`.trim()}
        />
      );
    }

    return (
      <header
        className={`flex shrink-0 items-center justify-between gap-3 border-b-[1px] border-border-master bg-surface-card px-4 py-2 ${stickyClass} ${className}`.trim()}
      >
        <div className="min-w-0">{breadcrumb}</div>
        {hasRight ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {badge}
            {actions}
          </div>
        ) : null}
      </header>
    );
  }

  return (
    <header
      className={`flex shrink-0 items-start justify-between gap-4 border-b-2 border-border-master bg-surface-card px-6 py-4 ${stickyClass} ${className}`.trim()}
    >
      <div className="min-w-0 flex-1">
        {breadcrumb ? <div className="mb-2">{breadcrumb}</div> : null}
        {phaseLabel ? (
          <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
            {phaseLabel}
          </p>
        ) : null}
        {title ? (
          <h1
            className={`${phaseLabel ? "mt-1" : ""} font-headline text-headline-md uppercase tracking-tighter text-ink-primary`.trim()}
          >
            {title}
          </h1>
        ) : null}
      </div>
      {hasRight ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {badge}
          {actions}
        </div>
      ) : null}
    </header>
  );
}
