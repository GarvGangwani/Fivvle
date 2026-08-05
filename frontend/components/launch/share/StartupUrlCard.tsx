"use client";

import { useToast } from "@/components/ui/ToastProvider";
import { LandingPageSlugEditor } from "@/components/launch/LandingPageSlugEditor";
import { DesignCollapsibleCard } from "@/components/launch/design/DesignCollapsibleCard";
import {
  buildPublicLandingPageUrl,
  formatPublicLandingHost,
} from "@/lib/landing-host";

type Props = {
  experimentId: string;
  slug: string;
  projectName: string;
  isLive: boolean;
  onSlugSaved: (slug: string) => void;
};

/**
 * Startup URL card — Option A1:
 * Card owns display + Copy/Open; LandingPageSlugEditor (embedded) owns Edit + Check.
 */
export function StartupUrlCard({
  experimentId,
  slug,
  projectName,
  isLive,
  onSlugSaved,
}: Props) {
  const { toast } = useToast();
  const publicHost = formatPublicLandingHost(slug);
  const publicUrl = buildPublicLandingPageUrl(slug);

  const copyLink = () => {
    void navigator.clipboard.writeText(publicUrl).then(() => {
      toast("Copied", "success");
    });
  };

  const openLive = () => {
    if (!isLive) return;
    window.open(publicUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <DesignCollapsibleCard title="Startup URL" defaultOpen>
      <div className="flex flex-col gap-4">
        <div>
          <a
            href={isLive ? publicUrl : undefined}
            target={isLive ? "_blank" : undefined}
            rel={isLive ? "noopener noreferrer" : undefined}
            onClick={(e) => {
              if (!isLive) e.preventDefault();
            }}
            className={`block truncate font-mono text-body-sm uppercase text-accent ${
              isLive ? "underline-offset-2 hover:underline" : "cursor-default"
            }`}
            title={publicHost}
          >
            {publicHost}
          </a>
          <p className="mt-1 font-mono text-mono-sm uppercase text-ink-tertiary">
            {isLive
              ? "Live — changing the URL updates your public link."
              : "Draft — publish to make this URL live."}
          </p>
        </div>

        {/* fv-* slug editor — brutalist border wrapper only (A1) */}
        <div className="border-2 border-border-master bg-surface-elevated p-3 shadow-brutal-sm">
          <LandingPageSlugEditor
            experimentId={experimentId}
            currentSlug={slug}
            projectName={projectName}
            isLive={isLive}
            embedded
            onSlugSaved={onSlugSaved}
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={copyLink}
            className="inline-flex items-center justify-center gap-1.5 border-2 border-border-master bg-surface-card px-3 py-2.5 font-label-md text-label-md uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md"
          >
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 16 }}
              aria-hidden="true"
            >
              content_copy
            </span>
            Copy link
          </button>
          <button
            type="button"
            disabled={!isLive}
            onClick={openLive}
            className="inline-flex items-center justify-center gap-1.5 border-2 border-border-master bg-surface-card px-3 py-2.5 font-label-md text-label-md uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-brutal-sm"
          >
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 16 }}
              aria-hidden="true"
            >
              open_in_new
            </span>
            Open
          </button>
        </div>
      </div>
    </DesignCollapsibleCard>
  );
}
