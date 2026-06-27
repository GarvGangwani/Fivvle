import type { ReactNode } from "react";

interface PageHeaderProps {
  title: ReactNode;
  description?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  /** Tighter spacing for full-height workspace views (e.g. experiment detail). */
  compact?: boolean;
}

export function PageHeader({
  title,
  description,
  badge,
  actions,
  compact = false,
}: PageHeaderProps) {
  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-3 ${
        compact ? "mb-2" : "mb-6 gap-4"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {typeof title === "string" ? (
            <h1
              className={`font-semibold tracking-[-0.02em] text-[var(--fv-text)] ${
                compact ? "text-lg sm:text-xl" : "text-xl sm:text-2xl"
              }`}
            >
              {title}
            </h1>
          ) : (
            title
          )}
          {badge}
        </div>
        {description && !compact && (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-[var(--fv-text-muted)]">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}
