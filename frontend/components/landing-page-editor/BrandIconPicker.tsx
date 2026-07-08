"use client";

import { useRef, useState } from "react";
import type { PageJson } from "@/lib/types";
import type { BrandIconMode, PageBranding } from "@/lib/branding";
import { resolveBranding, clampLogoScale } from "@/lib/branding";
import { ApiError, uploadProjectLogo } from "@/lib/api";
import { BrandMark } from "@/components/landing-templates/BrandMark";
import type { TemplateId } from "@/lib/templates";
import { DesignSlider } from "@/components/landing-page-editor/DesignSlider";

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
        setUploadError(err instanceof Error ? err.message : "Upload failed.");
      }
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
                : "border-[var(--fv-border)] hover:border-[var(--fv-border-strong)]"
            }`}
          >
            <p className="text-sm font-medium text-[var(--fv-text)]">{m.label}</p>
            <p className="text-[10px] text-[var(--fv-text-muted)]">{m.hint}</p>
          </button>
        ))}
      </div>

      {currentMode === "url" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-dashed border-[var(--fv-border)] bg-[color-mix(in_srgb,var(--fv-text)_3%,transparent)] p-4">
            <p className="text-xs font-medium text-[var(--fv-text-soft)]">Upload logo</p>
            <p className="mt-0.5 text-[10px] text-[var(--fv-text-muted)]">
              PNG, JPEG, or WebP · max {MAX_LOGO_MB} MB
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_LOGO_TYPES}
              disabled={disabled || uploading}
              className="mt-3 block w-full text-xs text-[var(--fv-text-soft)] file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--fv-accent)] file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-fv-bg hover:file:bg-[var(--fv-accent-hover)] disabled:opacity-50"
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
            <span className="text-xs text-[var(--fv-text-muted)]">Or paste image URL</span>
            <input
              type="url"
              disabled={disabled}
              placeholder="https://yoursite.com/logo.png"
              value={logoUrl}
              onChange={(e) => applyLogoUrl(e.target.value)}
              className="fv-input px-3 py-2 text-sm"
            />
            <p className="text-[10px] text-[var(--fv-text-dim)]">
              Square or horizontal logos on a transparent background work best.
            </p>
          </label>
        </div>
      )}

      {currentMode === "emoji" && (
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-[var(--fv-text-muted)]">Emoji</span>
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

      <DesignSlider
        label="Logo size"
        hint="Scales the mark in your landing page nav"
        value={branding.logo_scale}
        min={60}
        max={160}
        step={2}
        disabled={disabled}
        formatValue={(v) => `${v}%`}
        onChange={(logo_scale) =>
          apply({ branding: { logo_scale: clampLogoScale(logo_scale) } })
        }
      />

      <div className="rounded-lg border border-[var(--fv-border)] bg-[color-mix(in_srgb,var(--fv-text)_3%,transparent)] px-4 py-3">
        <p className="mb-2 text-[10px] uppercase tracking-wider text-[var(--fv-text-muted)]">
          Preview
        </p>
        <BrandMark
          branding={branding}
          projectName={projectName}
          variant={previewVariant}
          showSplitName={previewVariant === "dark-premium"}
          href={undefined}
        />
      </div>
    </div>
  );
}
