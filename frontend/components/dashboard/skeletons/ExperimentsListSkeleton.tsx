import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export function ExperimentsListSkeleton() {
  return (
    <div className="py-8" aria-busy="true" aria-label="Loading experiments">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <BrutalistSkeleton className="h-10 w-64 max-w-full" />
        <BrutalistSkeleton className="h-12 w-48" />
      </div>

      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <BrutalistSkeleton className="h-12 w-full max-w-md" />
        <div className="flex gap-3">
          <BrutalistSkeleton className="h-12 w-36" />
          <BrutalistSkeleton className="h-12 w-36" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="space-y-3 border-2 border-border-master bg-surface-card p-4"
          >
            <BrutalistSkeleton className="h-4 w-24" />
            <BrutalistSkeleton className="h-6 w-full" />
            <BrutalistSkeleton className="h-3 w-3/4" />
            <div className="flex items-center justify-between pt-3">
              <BrutalistSkeleton className="h-3 w-20" />
              <BrutalistSkeleton className="h-8 w-8" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
