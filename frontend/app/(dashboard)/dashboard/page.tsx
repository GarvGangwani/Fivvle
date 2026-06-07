import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { DashboardContent } from "@/components/dashboard/DashboardContent";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[calc(100vh-58px)] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
