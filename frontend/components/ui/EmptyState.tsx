import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`fv-fade-up flex flex-col items-center px-6 py-16 text-center ${className}`}
    >
      {icon && (
        <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--fv-accent-muted)] ring-1 ring-[color-mix(in_srgb,var(--fv-accent)_20%,transparent)]">
          {icon}
        </div>
      )}
      <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
        {title}
      </h2>
      {description && (
        <p className="mt-2 max-w-md text-sm leading-relaxed text-[var(--fv-text-muted)]">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
