export function AuthEmailDivider() {
  return (
    <div
      className="my-6 flex items-center gap-4"
      role="separator"
      aria-label="or use email"
    >
      <div className="flex-1 border-t border-dashed border-border-master" />
      <span className="whitespace-nowrap font-mono text-mono-sm uppercase tracking-wider text-ink-tertiary">
        OR USE EMAIL
      </span>
      <div className="flex-1 border-t border-dashed border-border-master" />
    </div>
  );
}
