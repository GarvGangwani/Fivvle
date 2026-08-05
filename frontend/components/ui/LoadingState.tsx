import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  label?: string;
  className?: string;
}

export function LoadingState({
  label = "Loading…",
  className = "",
}: LoadingStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-16 ${className}`}
    >
      <Loader2 className="h-6 w-6 animate-spin text-accent" />
      <p className="text-sm text-[var(--fv-text-muted)]">{label}</p>
    </div>
  );
}
