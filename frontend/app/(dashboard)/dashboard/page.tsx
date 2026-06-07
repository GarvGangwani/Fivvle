import { DashboardContent } from "@/components/dashboard/DashboardContent";

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--fv-text)]">Your experiments</h1>
        <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
          Track validation progress across all your ideas.
        </p>
      </div>

      <DashboardContent />
    </main>
  );
}
