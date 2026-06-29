import { AlertCircle, X } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorBanner({
  message,
  onDismiss,
  className = "",
}: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className={`fv-error flex items-start gap-3 ${className}`}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--fv-danger-light)]" />
      <p className="min-w-0 flex-1 text-sm leading-relaxed">{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="fv-icon-btn shrink-0 !h-7 !w-7"
          aria-label="Dismiss error"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
