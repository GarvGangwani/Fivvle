type BrutalistSkeletonVariant = "card" | "line" | "block" | "circle";

type Props = {
  variant?: BrutalistSkeletonVariant;
  /** Tailwind width class (e.g. `w-full`, `w-48`). */
  width?: string;
  /** Tailwind height class (e.g. `h-4`, `h-24`). */
  height?: string;
  className?: string;
};

const VARIANT_DEFAULTS: Record<
  BrutalistSkeletonVariant,
  { width: string; height: string; bordered: boolean; circle: boolean }
> = {
  card: { width: "w-full", height: "h-24", bordered: true, circle: false },
  line: { width: "w-full", height: "h-4", bordered: false, circle: false },
  block: { width: "w-full", height: "h-16", bordered: true, circle: false },
  circle: { width: "w-10", height: "h-10", bordered: true, circle: true },
};

/**
 * Brutalist loading placeholder. No chrome radius except `circle`.
 * Typography helpers remain elsewhere — this is shape-only.
 */
export function BrutalistSkeleton({
  variant = "line",
  width,
  height,
  className = "",
}: Props) {
  const defaults = VARIANT_DEFAULTS[variant];
  const w = width ?? defaults.width;
  const h = height ?? defaults.height;
  const border = defaults.bordered
    ? "border-2 border-border-master"
    : "border-0";
  const radius = defaults.circle ? "rounded-full" : "rounded-none";

  return (
    <div
      className={`bg-surface-elevated ${border} ${radius} ${h} ${w} animate-pulse motion-reduce:animate-none ${className}`.trim()}
      aria-hidden="true"
      data-variant={variant}
    />
  );
}
