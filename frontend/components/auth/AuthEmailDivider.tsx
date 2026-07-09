export function AuthEmailDivider() {
  return (
    <div className="w-full py-8">
      <div className="relative flex items-center justify-center">
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-1/2 -translate-y-1/2 border-t border-dashed border-border-master"
        />
        <span
          className="relative z-10 bg-surface-card px-4 font-mono text-mono-sm uppercase tracking-wider text-ink-tertiary"
          role="separator"
          aria-label="or use email"
        >
          OR USE EMAIL
        </span>
      </div>
    </div>
  );
}
