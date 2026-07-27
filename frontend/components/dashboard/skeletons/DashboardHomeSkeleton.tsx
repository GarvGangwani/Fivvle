import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export function DashboardHomeSkeleton() {
  return (
    <div className="py-8" aria-busy="true" aria-label="Loading dashboard">
      <BrutalistSkeleton
        variant="block"
        height="h-12"
        width="w-72"
        className="mb-8 max-w-full"
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <BrutalistSkeleton
          variant="card"
          height="h-72"
          className="lg:col-span-2"
        />
        <BrutalistSkeleton variant="card" height="h-72" />
      </div>

      <div className="mb-6 mt-12">
        <BrutalistSkeleton variant="line" width="w-48" />
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <BrutalistSkeleton key={i} variant="card" height="h-40" />
        ))}
      </div>

      <div className="mt-10 flex justify-center">
        <BrutalistSkeleton variant="block" height="h-14" width="w-56" />
      </div>
    </div>
  );
}
