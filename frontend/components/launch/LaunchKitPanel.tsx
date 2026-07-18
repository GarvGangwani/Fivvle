"use client";

import { useRef, useState } from "react";
import { ShareLinksPanel } from "@/components/distribution/ShareLinksPanel";
import { BrutalistEditableField } from "@/components/launch/BrutalistEditableField";
import { ChannelSelectPopover } from "@/components/launch/ChannelSelectPopover";
import { ShareCopyEditor } from "@/components/launch/ShareCopyEditor";
import type {
  LaunchChannel,
  LaunchKit,
  LaunchKitPatch,
} from "@/lib/api-launch-kit";
import {
  CHANNEL_LABELS,
  COHORT_HINT_MAX,
  RATIONALE_MAX,
} from "@/lib/launch-labels";

type Props = {
  launchKit: LaunchKit;
  slug: string | null;
  isLive: boolean;
  experimentName: string;
  onPatch: (
    update: LaunchKitPatch,
    options?: { fieldKey?: string },
  ) => Promise<void>;
  isSaving: (fieldKey: string) => boolean;
};

export function LaunchKitPanel({
  launchKit,
  slug,
  isLive,
  experimentName,
  onPatch,
  isSaving,
}: Props) {
  const [channelOpen, setChannelOpen] = useState(false);
  /** Channel present when this panel mounted — notice only after a founder change. */
  const channelAtMountRef = useRef(launchKit.first_channel);
  const channelAnchorRef = useRef<HTMLButtonElement>(null);
  const showChannelChangeNotice =
    launchKit.first_channel !== channelAtMountRef.current;

  const checklist = launchKit.readiness_checklist;
  const checkedCount = checklist.filter((item) => item.checked_at !== null)
    .length;

  function toggleChecklistItem(id: string, currentlyChecked: boolean) {
    const fieldKey = `readiness:${id}`;
    if (isSaving(fieldKey)) return;
    void onPatch(
      {
        readiness_checklist: [
          {
            id,
            checked_at: currentlyChecked ? null : new Date().toISOString(),
          },
        ],
      },
      { fieldKey },
    );
  }

  function handleChannelSelect(channel: LaunchChannel) {
    if (channel === launchKit.first_channel) return;
    void onPatch(
      { first_channel: channel },
      { fieldKey: "first_channel" },
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header — tab strip already labels Kit; micro-copy only */}
      <div className="shrink-0 border-b-2 border-border-master bg-surface-elevated px-6 py-4">
        <p className="font-mono text-mono-sm uppercase text-ink-primary/60">
          Ready to put this in front of people
        </p>
      </div>

      {/* Body */}
      <div className="min-h-0 flex-1 space-y-8 overflow-y-auto p-6">
        {/* Readiness checklist */}
        <section className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-md">
          <div className="mb-4 flex items-center justify-between">
            <span className="font-label-md text-label-md uppercase text-ink-primary">
              Readiness
            </span>
            <span className="font-mono text-mono-sm uppercase text-ink-primary/60">
              {checkedCount} / {checklist.length}
            </span>
          </div>
          <ul className="space-y-3">
            {checklist.map((item) => {
              const checked = item.checked_at !== null;
              const fieldKey = `readiness:${item.id}`;
              const saving = isSaving(fieldKey);
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => toggleChecklistItem(item.id, checked)}
                    disabled={saving}
                    className="flex w-full items-start gap-3 text-left disabled:opacity-60"
                    aria-pressed={checked}
                  >
                    <span
                      className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border-2 border-border-master ${
                        checked ? "bg-ink-primary" : "bg-transparent"
                      }`}
                      aria-hidden="true"
                    >
                      {checked ? (
                        <span
                          className="material-symbols-outlined text-ink-inverse"
                          style={{ fontSize: 14 }}
                        >
                          check
                        </span>
                      ) : null}
                    </span>
                    <span
                      className={`text-body-md text-ink-primary ${
                        checked ? "line-through opacity-60" : ""
                      }`}
                    >
                      {item.label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        {/* First channel */}
        <section className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-md">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-label-md text-label-md uppercase text-ink-primary">
              First Channel
            </span>
            <span
              className="material-symbols-outlined text-ink-primary/40"
              style={{ fontSize: 18 }}
              aria-hidden="true"
            >
              info
            </span>
          </div>
          <button
            ref={channelAnchorRef}
            type="button"
            onClick={() => setChannelOpen((o) => !o)}
            disabled={isSaving("first_channel")}
            className="flex w-full items-center justify-between text-left disabled:opacity-60"
            aria-haspopup="listbox"
            aria-expanded={channelOpen}
          >
            <span className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              {CHANNEL_LABELS[launchKit.first_channel]}
            </span>
            <span
              className="material-symbols-outlined text-ink-primary/50"
              aria-hidden="true"
            >
              expand_more
            </span>
          </button>
          <ChannelSelectPopover
            open={channelOpen}
            anchorRef={channelAnchorRef}
            current={launchKit.first_channel}
            onSelect={handleChannelSelect}
            onClose={() => setChannelOpen(false)}
          />
          {showChannelChangeNotice ? (
            <p className="mt-2 font-mono text-mono-sm text-ink-primary/50">
              Rationale and share copy still reflect the previous channel.
              Regenerate the kit to refresh.
            </p>
          ) : null}
          <div className="mt-4">
            <span className="mb-2 block font-label-sm text-label-sm uppercase text-ink-primary/60">
              Why this channel
            </span>
            <BrutalistEditableField
              value={launchKit.first_channel_rationale}
              softCap={RATIONALE_MAX}
              hardCap={RATIONALE_MAX}
              saving={isSaving("first_channel_rationale")}
              minRows={3}
              onSave={(text) =>
                void onPatch(
                  { first_channel_rationale: text },
                  { fieldKey: "first_channel_rationale" },
                )
              }
            />
          </div>
        </section>

        {/* First cohort */}
        <section className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-md">
          <span className="mb-3 block font-label-md text-label-md uppercase text-ink-primary">
            First Cohort
          </span>
          <BrutalistEditableField
            value={launchKit.first_cohort_hint}
            softCap={COHORT_HINT_MAX}
            hardCap={COHORT_HINT_MAX}
            saving={isSaving("first_cohort_hint")}
            minRows={3}
            onSave={(text) =>
              void onPatch(
                { first_cohort_hint: text },
                { fieldKey: "first_cohort_hint" },
              )
            }
          />
        </section>

        {/* Share copy */}
        <ShareCopyEditor
          variants={launchKit.share_copy_variants}
          isSaving={(index) => isSaving(`share_copy:${index}`)}
          onSaveVariant={(index, text) =>
            void onPatch(
              { share_copy_variants: [{ index, text }] },
              { fieldKey: `share_copy:${index}` },
            )
          }
        />

        {/* Trackable share links */}
        {isLive && slug ? (
          <section className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-md">
            <span className="mb-3 block font-label-md text-label-md uppercase text-ink-primary">
              Trackable Links
            </span>
            <ShareLinksPanel
              slug={slug}
              experimentName={experimentName}
              showDescription={false}
            />
          </section>
        ) : (
          <section className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-md">
            <span className="mb-2 block font-label-md text-label-md uppercase text-ink-primary">
              Trackable Links
            </span>
            <p className="font-mono text-mono-sm uppercase text-ink-primary/60">
              Trackable links appear here after you publish.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
