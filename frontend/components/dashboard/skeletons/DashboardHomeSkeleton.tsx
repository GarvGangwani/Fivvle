import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export function DashboardHomeSkeleton() {
  return (
    <div className="py-8" aria-busy="true" aria-label="Loading dashboard">
      <BrutalistSkeleton className="mb-8 h-12 w-72 max-w-full" />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <BrutalistSkeleton className="h-72 lg:col-span-2" />
        <BrutalistSkeleton className="h-72" />
      </div>

      <div className="mt-12 mb-6">
        <BrutalistSkeleton className="h-4 w-48" />
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <BrutalistSkeleton key={i} className="h-40" />
        ))}
      </div>

      <div className="mt-10 flex justify-center">
        <BrutalistSkeleton className="h-14 w-56" />
      </div>
    </div>
  );
}
