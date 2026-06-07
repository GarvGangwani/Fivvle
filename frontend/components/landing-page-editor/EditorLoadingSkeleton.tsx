export function EditorLoadingSkeleton() {
  return (
    <div className="flex min-h-[calc(100dvh-58px)] flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="fv-skeleton h-7 w-48 rounded-lg" />
        <div className="fv-skeleton h-6 w-24 rounded-full" />
      </div>
      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(280px,360px)_1fr]">
        <div className="space-y-4 rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-5">
          <div className="fv-skeleton h-5 w-40 rounded" />
          <div className="fv-skeleton h-10 w-full rounded-xl" />
          <div className="fv-skeleton h-24 w-full rounded-xl" />
          <div className="fv-skeleton h-10 w-full rounded-xl" />
          <div className="fv-skeleton h-5 w-32 rounded" />
          <div className="fv-skeleton h-10 w-full rounded-xl" />
          <div className="fv-skeleton h-32 w-full rounded-xl" />
        </div>
        <div className="fv-skeleton min-h-[480px] rounded-xl lg:min-h-[calc(100vh-12rem)]" />
      </div>
    </div>
  );
}
