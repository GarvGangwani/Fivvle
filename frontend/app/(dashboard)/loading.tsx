import { DashboardHomeSkeleton } from "@/components/dashboard/skeletons/DashboardHomeSkeleton";

/**
 * Route-level pending UI for `(dashboard)/*` page slots.
 * Layout already renders DashboardShell (sidebar + chrome), so this is
 * content-shaped only — avoids a double sidebar during soft navigations.
 */
export default function DashboardLoading() {
  return (
    <div className="px-6" aria-busy="true" aria-label="Loading">
      <DashboardHomeSkeleton />
    </div>
  );
}
