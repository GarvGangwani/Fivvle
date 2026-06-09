import { Suspense } from "react";
import { DashboardContent } from "@/components/dashboard/DashboardContent";

function DashboardSuspenseSkeleton() {
  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <aside
        className="hidden w-[260px] shrink-0 border-r p-4 md:block"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <div className="fv-skeleton h-10 rounded-xl" />
        <div className="mb-3 mt-5 px-1">
          <div className="fv-skeleton h-3 w-16 rounded" />
        </div>
        <div className="space-y-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="fv-skeleton h-14 rounded-lg" />
          ))}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8">
        <div className="fv-skeleton mb-4 h-8 w-48 rounded" />
        <div className="fv-skeleton h-64 rounded-xl" />
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSuspenseSkeleton />}>
      <DashboardContent />
    </Suspense>
  );
}
