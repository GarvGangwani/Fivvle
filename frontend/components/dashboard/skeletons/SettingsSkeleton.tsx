import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export function SettingsSkeleton() {
  return (
    <div
      className="mx-auto max-w-4xl space-y-12 px-gutter py-12"
      aria-busy="true"
      aria-label="Loading settings"
    >
      <div>
        <BrutalistSkeleton className="mb-3 h-10 w-48" />
        <BrutalistSkeleton className="h-5 w-80 max-w-full" />
      </div>

      <div className="space-y-6">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="space-y-4 rounded-md border-2 border-border-master bg-surface-card p-6"
          >
            <BrutalistSkeleton className="h-4 w-32" />
            <BrutalistSkeleton className="h-3 w-full" />
            <BrutalistSkeleton className="h-3 w-4/5" />
            <BrutalistSkeleton className="mt-4 h-10 w-40" />
          </div>
        ))}
      </div>
    </div>
  );
}
