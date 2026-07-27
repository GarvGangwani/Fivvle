import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export function ExperimentsListSkeleton() {
  return (
    <div className="py-8" aria-busy="true" aria-label="Loading experiments">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <BrutalistSkeleton
          variant="block"
          height="h-10"
          width="w-64"
          className="max-w-full"
        />
        <BrutalistSkeleton variant="block" height="h-12" width="w-48" />
      </div>

      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <BrutalistSkeleton
          variant="block"
          height="h-12"
          className="max-w-md"
        />
        <div className="flex gap-3">
          <BrutalistSkeleton variant="block" height="h-12" width="w-36" />
          <BrutalistSkeleton variant="block" height="h-12" width="w-36" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="space-y-3 border-2 border-border-master bg-surface-card p-4"
          >
            <BrutalistSkeleton variant="line" width="w-24" />
            <BrutalistSkeleton variant="block" height="h-6" />
            <BrutalistSkeleton variant="line" width="w-3/4" />
            <div className="flex items-center justify-between pt-3">
              <BrutalistSkeleton variant="line" width="w-20" />
              <BrutalistSkeleton variant="circle" height="h-8" width="w-8" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
