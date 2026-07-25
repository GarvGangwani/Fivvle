"use client";

import { useState, type ReactNode } from "react";

type Props = {
  title: string;
  defaultOpen?: boolean;
  headerActions?: ReactNode;
  children: ReactNode;
};

/**
 * Brutalist collapsible card for Launch Design panels.
 * Local open state only — no localStorage.
 */
export function DesignCollapsibleCard({
  title,
  defaultOpen = true,
  headerActions,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="border-2 border-border-master bg-surface-card shadow-brutal-sm">
      <div className="flex items-center gap-2 border-b-2 border-border-master px-3 py-2.5">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <span
            className="material-symbols-outlined shrink-0 text-ink-primary transition-transform"
            style={{
              fontSize: 18,
              transform: open ? "rotate(0deg)" : "rotate(-90deg)",
            }}
            aria-hidden="true"
          >
            expand_more
          </span>
          <h3 className="truncate font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
            {title}
          </h3>
        </button>
        {headerActions ? (
          <div
            className="flex shrink-0 items-center gap-1.5"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            {headerActions}
          </div>
        ) : null}
      </div>
      {open ? <div className="p-3">{children}</div> : null}
    </section>
  );
}
