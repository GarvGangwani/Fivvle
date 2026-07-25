"use client";

import { useToast } from "@/components/ui/ToastProvider";
import { buildTrackedLandingPageUrl } from "@/lib/published-page";

export const SHARE_CHANNELS = [
  { label: "Twitter / X", tag: "twitter" },
  { label: "LinkedIn", tag: "linkedin" },
  { label: "Reddit", tag: "reddit" },
  { label: "Email", tag: "email" },
  { label: "Friends & family", tag: "warm" },
] as const;

interface ShareLinksPanelProps {
  slug: string;
  experimentName: string;
  showDescription?: boolean;
  /** Optional — e.g. Kit auto-tick `tracking_on` after a founder copies a link. */
  onLinkCopied?: () => void;
}

export function ShareLinksPanel({
  slug,
  experimentName,
  showDescription = true,
  onLinkCopied,
}: ShareLinksPanelProps) {
  const { toast } = useToast();

  function handleCopy(url: string, channelLabel: string) {
    void navigator.clipboard.writeText(url).then(() => {
      toast(`${channelLabel} link copied`, "success");
      onLinkCopied?.();
    });
  }

  return (
    <div>
      {showDescription && (
        <>
          <p className="fv-panel-label mb-3">Share with tracking</p>
          <p className="mb-3 text-[12px] text-[var(--fv-text-muted)]">
            Each link tracks which channel drives traffic. Use these when sharing{" "}
            <span className="font-medium text-[var(--fv-text-soft)]">
              {experimentName}
            </span>
            .
          </p>
        </>
      )}
      <div className="space-y-2">
        {SHARE_CHANNELS.map(({ label, tag }) => {
          const url = buildTrackedLandingPageUrl(slug, tag);
          return (
            <div
              key={tag}
              className="flex flex-col gap-2 sm:flex-row sm:items-center"
            >
              <span className="shrink-0 text-[13px] text-[var(--fv-text-soft)] sm:w-28">
                {label}
              </span>
              <code className="min-w-0 flex-1 truncate rounded-lg bg-[var(--fv-surface-2)] px-3 py-2 font-mono text-[12px] text-[var(--fv-text-muted)]">
                {url}
              </code>
              <button
                type="button"
                onClick={() => handleCopy(url, label)}
                className="fv-btn-ghost min-h-[44px] shrink-0 px-3 py-1.5 text-[12px] transition-all duration-200 sm:min-h-0"
              >
                Copy
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
