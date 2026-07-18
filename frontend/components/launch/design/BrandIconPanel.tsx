"use client";

import { useEffect, useRef, useState } from "react";
import type { PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import {
  clampLogoScale,
  projectInitials,
  resolveBranding,
  type BrandIconMode,
  type PageBranding,
} from "@/lib/branding";
import { applyBrandingPatch } from "@/lib/landing-design";
import { ApiError, uploadProjectLogo } from "@/lib/api";
import { BrandMark, type BrandMarkVariant } from "@/components/landing-templates/BrandMark";
import { DesignCollapsibleCard } from "./DesignCollapsibleCard";
import { BrutalistSlider } from "./BrutalistSlider";

const MODES: { id: BrandIconMode; label: string; hint: string }[] = [
  { id: "initials", label: "Initials", hint: "Letters from your project name" },
  { id: "url", label: "Logo image", hint: "Upload a file or paste a URL" },
  { id: "emoji", label: "Emoji", hint: "Single emoji as your mark" },
  { id: "mark", label: "Template mark", hint: "Built-in shape (Bold only)" },
];

const ACCEPTED = "image/png,image/jpeg,image/webp";
const MAX_MB = 2;

type Props = {
  experimentId: string;
  templateId: TemplateId;
  projectName: string;
  page: PageJson;
  disabled?: boolean;
  onChange: (nextPage: PageJson) => void;
};

function brandMarkVariant(templateId: TemplateId): BrandMarkVariant {
  if (
    templateId === "bold-v1" ||
    templateId === "minimal-v3" ||
    templateId === "editorial-saas" ||
    templateId === "aether"
  ) {
    return templateId;
  }
  return "dark-premium";
}

export function BrandIconPanel({
  experimentId,
  templateId,
  projectName,
  page,
  disabled,
  onChange,
}: Props) {
  const b = page.branding as PageBranding | undefined;
  const branding = resolveBranding(page, projectName);
  const currentMode = b?.icon_mode ?? branding.icon_mode;

  const [logoUrl, setLogoUrl] = useState(b?.logo_url ?? "");
  const [logoEmoji, setLogoEmoji] = useState(b?.logo_emoji ?? "");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setLogoUrl(b?.logo_url ?? "");
    setLogoEmoji(b?.logo_emoji ?? "");
  }, [b?.logo_url, b?.logo_emoji]);

  const apply = (patch: Partial<PageBranding>) => {
    onChange(applyBrandingPatch(page, patch, projectName));
  };

  const showMark = templateId === "bold-v1";
  const modes = MODES.filter((m) => m.id !== "mark" || showMark);

  const handleUpload = async (file: File | null) => {
    if (!file) return;
    setUploadError(null);
    if (!file.type.match(/^image\/(png|jpeg|webp)$/)) {
      setUploadError("Use a PNG, JPEG, or WebP image.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setUploadError(`Image must be ${MAX_MB} MB or smaller.`);
      return;
    }
    setUploading(true);
    try {
      const { logo_url } = await uploadProjectLogo(experimentId, file);
      setLogoUrl(logo_url);
      apply({ icon_mode: "url", logo_url });
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body;
        const detail =
          body &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail?: unknown }).detail === "string"
            ? (body as { detail: string }).detail
            : null;
        setUploadError(detail ?? `Upload failed (${err.status}).`);
      } else {
        setUploadError("Upload failed.");
      }
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <DesignCollapsibleCard title="Brand icon" defaultOpen={false}>
      <p className="mb-3 font-mono text-mono-sm uppercase text-ink-primary/60">
        Logo or mark shown in the nav on your landing page.
      </p>

      <div className="mb-4 grid grid-cols-2 gap-2">
        {modes.map((m) => {
          const active = currentMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              disabled={disabled}
              onClick={() => apply({ icon_mode: m.id })}
              className={`border-2 border-border-master p-2.5 text-left transition-all disabled:opacity-50 ${
                active
                  ? "bg-brutalist-yellow shadow-brutal-sm"
                  : "bg-surface-elevated hover:-translate-y-0.5 hover:shadow-brutal-sm"
              }`}
            >
              <p className="font-label-sm text-label-sm uppercase tracking-wider text-ink-primary">
                {m.label}
              </p>
              <p className="mt-0.5 font-mono text-mono-sm uppercase text-ink-tertiary">
                {m.hint}
              </p>
            </button>
          );
        })}
      </div>

      {currentMode === "url" ? (
        <div className="mb-4 flex flex-col gap-3 border-2 border-dashed border-border-master p-3">
          <div>
            <p className="font-label-sm text-label-sm uppercase text-ink-primary/60">
              Upload logo
            </p>
            <p className="mt-0.5 font-mono text-mono-sm uppercase text-ink-tertiary">
              PNG, JPEG, or WebP · max {MAX_MB} MB
            </p>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED}
              disabled={disabled || uploading}
              className="mt-2 block w-full font-mono text-mono-sm text-ink-primary file:mr-2 file:border-2 file:border-border-master file:bg-brutalist-yellow file:px-2 file:py-1 file:font-label-sm file:uppercase"
              onChange={(e) => void handleUpload(e.target.files?.[0] ?? null)}
            />
            {uploading ? (
              <p className="mt-1 font-mono text-mono-sm uppercase text-ink-tertiary">
                Uploading…
              </p>
            ) : null}
            {uploadError ? (
              <p className="mt-1 font-mono text-mono-sm uppercase text-status-critical">
                {uploadError}
              </p>
            ) : null}
          </div>
          <div>
            <p className="mb-1 font-label-sm text-label-sm uppercase text-ink-primary/60">
              Or paste image URL
            </p>
            <input
              type="url"
              disabled={disabled}
              placeholder="https://…"
              value={logoUrl}
              onChange={(e) => {
                const v = e.target.value;
                setLogoUrl(v);
                apply({
                  icon_mode: "url",
                  logo_url: v.trim() || undefined,
                });
              }}
              className="w-full border-2 border-border-master bg-surface-elevated px-2 py-1.5 font-mono text-body-sm outline-none focus:border-brand-primary disabled:opacity-50"
            />
          </div>
        </div>
      ) : null}

      {currentMode === "emoji" ? (
        <div className="mb-4">
          <p className="mb-1 font-label-sm text-label-sm uppercase text-ink-primary/60">
            Emoji
          </p>
          <input
            type="text"
            disabled={disabled}
            maxLength={4}
            placeholder="🚀"
            value={logoEmoji}
            onChange={(e) => {
              const v = e.target.value;
              setLogoEmoji(v);
              apply({
                icon_mode: "emoji",
                logo_emoji: v.trim() || undefined,
              });
            }}
            className="w-20 border-2 border-border-master bg-surface-elevated px-2 py-1.5 text-center text-2xl outline-none focus:border-brand-primary disabled:opacity-50"
          />
        </div>
      ) : null}

      {currentMode === "initials" ? (
        <p className="mb-4 font-mono text-mono-sm uppercase text-ink-tertiary">
          Using initials: {projectInitials(projectName)}
        </p>
      ) : null}

      <div className="mb-4">
        <BrutalistSlider
          label="Logo size"
          hint="Scales the mark in your landing page nav"
          value={branding.logo_scale}
          min={60}
          max={160}
          step={2}
          disabled={disabled}
          onChange={(logo_scale) =>
            apply({ logo_scale: clampLogoScale(logo_scale) })
          }
        />
      </div>

      <div className="border-2 border-border-master bg-surface-elevated p-3">
        <p className="mb-2 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/60">
          Preview
        </p>
        <BrandMark
          branding={branding}
          projectName={projectName}
          variant={brandMarkVariant(templateId)}
        />
      </div>
    </DesignCollapsibleCard>
  );
}
