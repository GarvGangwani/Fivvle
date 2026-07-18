"use client";

import {
  ShareLinksPanel,
  SHARE_CHANNELS,
} from "@/components/distribution/ShareLinksPanel";
import { DesignCollapsibleCard } from "@/components/launch/design/DesignCollapsibleCard";

type Props = {
  slug: string;
  experimentName: string;
  isLive: boolean;
};

export function ShareWithTrackingCard({
  slug,
  experimentName,
  isLive,
}: Props) {
  return (
    <DesignCollapsibleCard
      title="Share with tracking"
      defaultOpen
      headerActions={
        <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
          {SHARE_CHANNELS.length} channel links
        </span>
      }
    >
      {isLive ? (
        <ShareLinksPanel
          slug={slug}
          experimentName={experimentName}
          showDescription={false}
        />
      ) : (
        <div className="border-2 border-border-master bg-surface-elevated p-6 text-center shadow-brutal-sm">
          <p className="font-mono text-mono-sm uppercase text-ink-primary/60">
            Publish your landing page to generate trackable share links.
          </p>
        </div>
      )}
    </DesignCollapsibleCard>
  );
}
