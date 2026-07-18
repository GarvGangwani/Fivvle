"use client";

import { useState } from "react";
import { useToast } from "@/components/ui/ToastProvider";
import { BrutalistEditableField } from "@/components/launch/BrutalistEditableField";
import type { ShareCopyVariant, ShareSurface } from "@/lib/api-launch-kit";
import {
  SCHEMA_TEXT_HARD_CAP,
  SHARE_COPY_SOFT_CAP,
  SURFACE_LABELS,
} from "@/lib/launch-labels";

type Props = {
  variants: ShareCopyVariant[];
  onSaveVariant: (index: number, text: string) => void;
  isSaving: (index: number) => boolean;
};

export function ShareCopyEditor({ variants, onSaveVariant, isSaving }: Props) {
  const { toast } = useToast();
  const [activeSurface, setActiveSurface] = useState(0);
  const activeVariant = variants[activeSurface] ?? variants[0];
  const softCap = activeVariant
    ? SHARE_COPY_SOFT_CAP[activeVariant.surface as ShareSurface]
    : SCHEMA_TEXT_HARD_CAP;

  function handleCopy() {
    if (!activeVariant) return;
    void navigator.clipboard.writeText(activeVariant.text).then(() => {
      toast("Share copy copied", "success");
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
        <BrutalistEditableField
          key={`${activeVariant.surface}-${activeSurface}`}
          value={activeVariant.text}
          softCap={softCap}
          hardCap={SCHEMA_TEXT_HARD_CAP}
          saving={isSaving(activeSurface)}
          minRows={5}
          onSave={(text) => onSaveVariant(activeSurface, text)}
        />
      ) : null}
    </section>
  );
}
