"use client";

import { useRef, useState } from "react";
import type { PageJson } from "@/lib/types";
import type { BrandIconMode, PageBranding } from "@/lib/branding";
import { resolveBranding } from "@/lib/branding";
import { uploadProjectLogo } from "@/lib/api";
import { BrandMark } from "@/components/landing-templates/BrandMark";
import type { TemplateId } from "@/lib/templates";

const MODES: { id: BrandIconMode; label: string; hint: string }[] = [
  { id: "initials", label: "Initials", hint: "Letters from your project name" },
  { id: "url", label: "Logo image", hint: "Upload a file or paste an image URL" },
  { id: "emoji", label: "Emoji", hint: "Single emoji as your mark" },
  { id: "mark", label: "Template mark", hint: "Use the built-in shape (Bold only)" },
];

const ACCEPTED_LOGO_TYPES = "image/png,image/jpeg,image/webp";
const MAX_LOGO_MB = 2;

export interface BrandingPatch {
  branding?: Partial<PageBranding>;
}

interface BrandIconPickerProps {
  projectId: string;
  templateId: TemplateId;
  projectName: string;
  page: PageJson;
  disabled?: boolean;
  onChange: (patch: BrandingPatch, nextPage: PageJson) => void;
  onPersist: (patch: BrandingPatch) => void;
}

export function BrandIconPicker({
  projectId,
  templateId,
  projectName,
  page,
  disabled,
  onChange,
  onPersist,
}: BrandIconPickerProps) {
  const b = page.branding as PageBranding | undefined;
  const [logoUrl, setLogoUrl] = useState(b?.logo_url ?? "");
  const [logoEmoji, setLogoEmoji] = useState(b?.logo_emoji ?? "");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const branding = resolveBranding(page, projectName);
  const currentMode = b?.icon_mode ?? branding.icon_mode;

  const apply = (patch: BrandingPatch) => {
    const nextPage: PageJson = {
      ...page,
      branding: {
        ...(page.branding as PageBranding | undefined),
        ...(patch.branding ?? {}),
        logo_alt: projectName,
      },
    };
    onChange(patch, nextPage);
    onPersist(patch);
  };

  const setMode = (mode: BrandIconMode) => {
    apply({ branding: { icon_mode: mode } });
  };

  const applyLogoUrl = (url: string) => {
    setLogoUrl(url);
    apply({
      branding: {
        icon_mode: "url",
        logo_url: url.trim() || undefined,
      },
    });
  };

  const handleFileSelect = async (file: File | null) => {
    if (!file) return;
    setUploadError(null);

    if (!file.type.match(/^image\/(png|jpeg|webp)$/)) {
      setUploadError("Use a PNG, JPEG, or WebP image.");
      return;
    }
    if (file.size > MAX_LOGO_MB * 1024 * 1024) {
      setUploadError(`Image must be ${MAX_LOGO_MB} MB or smaller.`);
      return;
    }

    setUploading(true);
    try {
      const { logo_url } = await uploadProjectLogo(projectId, file);
      applyLogoUrl(logo_url);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const previewVariant =
    templateId === "bold-v1"
      ? "bold-v1"
      : templateId === "minimal-v3"
        ? "minimal-v3"
        : templateId === "editorial-saas"
          ? "editorial-saas"
          : templateId === "aether"
            ? "aether"
            : "dark-premium";

  const showMarkMode = templateId === "bold-v1";

  return (
    <div className="space-y-4">
      <div>
        <p className="fv-panel-label">Brand icon</p>
        <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
          Logo or mark shown in the nav on your landing page.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {MODES.filter((m) => m.id !== "mark" || showMarkMode).map((m) => (
          <button
            key={m.id}
            type="button"
            disabled={disabled}
            onClick={() => setMode(m.id)}
            className={`rounded-lg border px-3 py-2 text-left transition-colors disabled:opacity-50 ${
              currentMode === m.id
                ? "border-[var(--fv-accent)]/50 bg-[var(--fv-accent-muted)]"
                : "border-white/10 hover:border-white/20"
            }`}
          >
            <p className="text-sm font-medium text-zinc-200">{m.label}</p>
            <p className="text-[10px] text-zinc-500">{m.hint}</p>
          </button>
        ))}
      </div>

      {currentMode === "url" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-dashed border-white/15 bg-black/20 p-4">
            <p className="text-xs font-medium text-zinc-400">Upload logo</p>
            <p className="mt-0.5 text-[10px] text-zinc-600">
              PNG, JPEG, or WebP · max {MAX_LOGO_MB} MB
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_LOGO_TYPES}
              disabled={disabled || uploading}
              className="mt-3 block w-full text-xs text-zinc-400 file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--fv-accent)] file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-[#080c14] hover:file:bg-[var(--fv-accent-hover)] disabled:opacity-50"
              onChange={(e) => void handleFileSelect(e.target.files?.[0] ?? null)}
            />
            {uploading && (
              <p className="mt-2 text-xs text-[var(--fv-accent)]">Uploading…</p>
            )}
            {uploadError && (
              <p className="mt-2 text-xs text-red-400">{uploadError}</p>
            )}
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-zinc-500">Or paste image URL</span>
            <input
              type="url"
              disabled={disabled}
              placeholder="https://yoursite.com/logo.png"
              value={logoUrl}
              onChange={(e) => applyLogoUrl(e.target.value)}
              className="fv-input px-3 py-2 text-sm"
            />
            <p className="text-[10px] text-zinc-600">
              Square or horizontal logos on a transparent background work best.
            </p>
          </label>
        </div>
      )}

      {currentMode === "emoji" && (
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-zinc-500">Emoji</span>
          <input
            type="text"
            disabled={disabled}
            maxLength={4}
            placeholder="🚀"
            value={logoEmoji}
            onChange={(e) => {
              const v = e.target.value;
              setLogoEmoji(v);
              apply({ branding: { logo_emoji: v.trim() || undefined } });
            }}
            className="fv-input w-24 px-3 py-2 text-2xl"
          />
        </label>
      )}

      <div className="rounded-lg border border-white/10 bg-black/30 px-4 py-3">
        <p className="mb-2 text-[10px] uppercase tracking-wider text-zinc-600">
          Preview
        </p>
        <BrandMark
          branding={resolveBranding(page, projectName)}
          projectName={projectName}
          variant={previewVariant}
          showSplitName={previewVariant === "dark-premium"}
          href={undefined}
        />
      </div>
    </div>
  );
}
