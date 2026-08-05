export function LiveActivityBadge() {
  // TODO: wire to real live-counter endpoint (tracked-work item #6)
  const count = 3;

  return (
    <aside
      className="absolute bottom-8 left-8 z-20 hidden max-w-xs rounded-md border-2 border-border-master bg-surface-card p-4 shadow-brutal-md lg:block"
      aria-label="Live validation activity"
    >
      <div className="flex items-center gap-2">
        <span
          className="relative flex h-2.5 w-2.5 shrink-0"
          aria-hidden="true"
        >
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60 motion-reduce:animate-none" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
        </span>
        <span className="font-label-md text-label-md uppercase text-accent">
          ACTIVE VALIDATION
        </span>
      </div>
      <p className="mt-2 font-body-md text-body-md text-ink-secondary">
        Fetching {count} experiments running right now
      </p>
    </aside>
  );
}
