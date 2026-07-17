type Props = {
  className?: string;
  variant?: "block" | "text" | "circle";
  animate?: boolean;
};

export function BrutalistSkeleton({
  className = "",
  variant = "block",
  animate = true,
}: Props) {
  const base =
    "bg-surface-elevated border-2 border-border-master rounded-md";
  const shape = variant === "circle" ? "!rounded-full" : "";
  const shimmer = animate ? "animate-pulse motion-reduce:animate-none" : "";

  return (
    <div
      className={`${base} ${shape} ${shimmer} ${className}`.trim()}
      aria-hidden="true"
    />
  );
}
