interface EditorLoadingSkeletonProps {
  embedded?: boolean;
}

export function EditorLoadingSkeleton({
  embedded = false,
}: EditorLoadingSkeletonProps) {
  return (
    <div
      className={`flex flex-col gap-4 ${
        embedded ? "h-full min-h-0 p-0" : "min-h-[calc(100dvh-58px)] px-4 py-4 sm:px-6 sm:py-6"
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="fv-skeleton h-7 w-48 rounded-lg" />
        <div className="fv-skeleton h-6 w-24 rounded-full" />
      </div>
      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(360px,440px)_1fr] xl:grid-cols-[minmax(400px,480px)_1fr]">
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
