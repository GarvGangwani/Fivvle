"use client";

/** Placeholder until PR 5.3 ships the Design tab body. */
export function LaunchDesignTabPlaceholder() {
  return (
    <div className="flex h-full min-h-0 items-center justify-center p-6">
      <div className="max-w-xs border-2 border-border-master bg-surface-card p-8 text-center shadow-brutal-md">
        <p className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
          Design
        </p>
        <p className="mt-2 font-mono text-mono-sm uppercase text-ink-primary/60">
          Design panel coming in PR 5.3
        </p>
      </div>
    </div>
  );
}
