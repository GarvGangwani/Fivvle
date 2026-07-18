"use client";

/** Placeholder until PR 5.4 ships the Share tab body. */
export function LaunchShareTabPlaceholder() {
  return (
    <div className="flex h-full min-h-0 items-center justify-center p-6">
      <div className="max-w-xs border-2 border-border-master bg-surface-card p-8 text-center shadow-brutal-md">
        <p className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
          Share
        </p>
        <p className="mt-2 font-mono text-mono-sm uppercase text-ink-primary/60">
          Share panel coming in PR 5.4
        </p>
      </div>
    </div>
  );
}
