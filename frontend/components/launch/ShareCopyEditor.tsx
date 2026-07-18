"use client";

import { useState } from "react";
import { useToast } from "@/components/ui/ToastProvider";
import { BrutalistEditableField } from "@/components/launch/BrutalistEditableField";
import type { ShareCopyVariant, ShareSurface } from "@/lib/api-launch-kit";
import { buildSharePostAction } from "@/lib/launch-channel-intents";
import {
  SCHEMA_TEXT_HARD_CAP,
  SHARE_COPY_SOFT_CAP,
  SURFACE_LABELS,
} from "@/lib/launch-labels";

type Props = {
  variants: ShareCopyVariant[];
  onSaveVariant: (index: number, text: string) => void;
  isSaving: (index: number) => boolean;
  experimentName: string;
  slug: string | null;
  isLive: boolean;
  /** Fired after plain COPY or a post-action that copies to clipboard. */
  onCopied?: () => void;
  /** Fired after a PREFILL post opens (or copy-open / degraded copy succeeds). */
  onPosted?: () => void;
};

export function ShareCopyEditor({
  variants,
  onSaveVariant,
  isSaving,
  experimentName,
  slug,
  isLive,
  onCopied,
  onPosted,
}: Props) {
  const { toast } = useToast();
  const [activeSurface, setActiveSurface] = useState(0);
  const activeVariant = variants[activeSurface] ?? variants[0];
  const softCap = activeVariant
    ? SHARE_COPY_SOFT_CAP[activeVariant.surface as ShareSurface]
    : SCHEMA_TEXT_HARD_CAP;

  const postAction = activeVariant
    ? buildSharePostAction({
        surface: activeVariant.surface as ShareSurface,
        text: activeVariant.text,
        experimentName,
        slug,
        isLive,
      })
    : null;

  function handleCopy() {
    if (!activeVariant) return;
    void navigator.clipboard.writeText(activeVariant.text).then(() => {
      toast("Share copy copied", "success");
      onCopied?.();
    });
  }

  function handlePostAction() {
    if (!activeVariant || !postAction) return;

    if (postAction.mode === "prefill") {
      if (postAction.openUrl) {
        window.open(postAction.openUrl, "_blank", "noopener,noreferrer");
      }
      onPosted?.();
      return;
    }

    void navigator.clipboard.writeText(postAction.clipboardText).then(() => {
      if (postAction.toastMessage) {
        toast(postAction.toastMessage, "success");
      }
      if (postAction.openUrl) {
        window.open(postAction.openUrl, "_blank", "noopener,noreferrer");
      }
      onPosted?.();
      onCopied?.();
    });
  }

  return (
    <section className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-md">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="font-label-md text-label-md uppercase text-ink-primary">
          Share Copy
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 border-2 border-border-master bg-surface-card px-2 py-1 font-label-sm text-label-sm uppercase text-ink-primary shadow-brutal-sm transition-all hover:shadow-brutal-md"
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 14 }}
            aria-hidden="true"
          >
            content_copy
          </span>
          Copy
        </button>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        {variants.map((variant, index) => {
          const active = index === activeSurface;
          return (
            <button
              key={`${variant.surface}-${index}`}
              type="button"
              onClick={() => setActiveSurface(index)}
              aria-pressed={active}
              className={`border-2 border-border-master px-3 py-1 font-label-sm text-label-sm uppercase transition-all ${
                active
                  ? "bg-brutalist-yellow text-ink-primary shadow-brutal-md"
                  : "bg-surface-card text-ink-primary/70"
              }`}
            >
              {SURFACE_LABELS[variant.surface]}
            </button>
          );
        })}
      </div>

      {activeVariant ? (
        <>
          <BrutalistEditableField
            key={`${activeVariant.surface}-${activeSurface}`}
            value={activeVariant.text}
            softCap={softCap}
            hardCap={SCHEMA_TEXT_HARD_CAP}
            saving={isSaving(activeSurface)}
            minRows={5}
            onSave={(text) => onSaveVariant(activeSurface, text)}
          />
          {postAction ? (
            <div className="mt-3">
              <button
                type="button"
                onClick={handlePostAction}
                className="w-full border-2 border-border-master bg-surface-card px-3 py-2 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-y-0.5 hover:shadow-brutal-md"
              >
                {postAction.buttonLabel}
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
