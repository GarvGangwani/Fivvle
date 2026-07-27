import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export function SettingsSkeleton() {
  return (
    <div
      className="mx-auto max-w-4xl space-y-12 px-gutter pb-12 pt-24"
      aria-busy="true"
      aria-label="Loading settings"
    >
      <div>
        <BrutalistSkeleton
          variant="block"
          height="h-10"
          width="w-48"
          className="mb-3"
        />
        <BrutalistSkeleton
          variant="line"
          height="h-5"
          width="w-80"
          className="max-w-full"
        />
      </div>

      <div className="space-y-6">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="space-y-4 border-2 border-border-master bg-surface-card p-6"
          >
            <BrutalistSkeleton variant="line" width="w-32" />
            <BrutalistSkeleton variant="line" height="h-3" />
            <BrutalistSkeleton variant="line" height="h-3" width="w-4/5" />
            <BrutalistSkeleton
              variant="block"
              height="h-10"
              width="w-40"
              className="mt-4"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
