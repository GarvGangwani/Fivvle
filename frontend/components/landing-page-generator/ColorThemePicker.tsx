"use client";

import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import {
  extractColorsFromBrand,
  getPresetsForTemplate,
  resolveColorPalette,
  type ColorMode,
  type UserColorPalette,
} from "@/lib/color-palettes";
import { downloadExportHtml } from "@/lib/export-page";

export interface ThemePatch {
  color_mode?: ColorMode;
  color_palette?: Partial<UserColorPalette>;
}

interface ColorThemePickerProps {
  templateId: TemplateId;
  page: PageJson;
  copy: CopyJson;
  projectName: string;
  brandVisualDirection?: string;
  disabled?: boolean;
  onChange: (patch: ThemePatch, nextPage: PageJson) => void;
  onPersist: (patch: ThemePatch) => void;
}

function Swatch({
  color,
  active,
  label,
  onClick,
  disabled,
}: {
  color: string;
  active: boolean;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={`h-9 w-9 rounded-lg border-2 transition-all disabled:opacity-50 ${
        active ? "border-[var(--fv-accent)] scale-110" : "border-white/20 hover:border-white/40"
      }`}
      style={{ background: color }}
    />
  );
}

function ColorField({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs text-zinc-500">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 w-9 cursor-pointer rounded border border-white/15 bg-transparent p-0.5 disabled:opacity-50"
        />
        <input
          type="text"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 rounded-lg border border-white/10 bg-black/40 px-2 py-1.5 font-mono text-xs text-zinc-300 outline-none focus:border-[var(--fv-accent)]/50 disabled:opacity-50"
        />
      </div>
    </label>
  );
}

export function ColorThemePicker({
  templateId,
  page,
  copy,
  projectName,
  brandVisualDirection,
  disabled,
  onChange,
  onPersist,
}: ColorThemePickerProps) {
  const palette = resolveColorPalette(page, templateId);
  const colorMode = (page.color_mode ?? "light") as ColorMode;
  const presets = getPresetsForTemplate(templateId);

  const apply = (patch: ThemePatch) => {
    const nextPage: PageJson = {
      ...page,
      ...(patch.color_mode !== undefined ? { color_mode: patch.color_mode } : {}),
      color_palette: {
        ...palette,
        ...(patch.color_palette ?? {}),
      },
    };
    onChange(patch, nextPage);
    onPersist(patch);
  };

  const selectPreset = (preset: UserColorPalette & { id?: string }) => {
    apply({
      color_palette: {
        preset: preset.preset,
        accent: preset.accent,
        background: preset.background,
        foreground: preset.foreground,
      },
    });
  };

  const updateColor = (key: keyof UserColorPalette, value: string) => {
    apply({
      color_palette: {
        preset: "custom",
        [key]: value,
      },
    });
  };

  const toggleMode = () => {
    apply({ color_mode: colorMode === "dark" ? "light" : "dark" });
  };

  const importFromBrand = () => {
    if (!brandVisualDirection?.trim()) return;
    const extracted = extractColorsFromBrand(brandVisualDirection);
    if (!extracted.accent) return;
    apply({
      color_palette: {
        preset: "brand",
        accent: extracted.accent ?? palette.accent,
        background: extracted.background ?? palette.background,
        foreground: extracted.foreground ?? palette.foreground,
      },
    });
  };

  const handleExport = () => {
    downloadExportHtml(copy, page, projectName, templateId);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="fv-panel-label">Color theme</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={disabled || !brandVisualDirection?.trim()}
            onClick={importFromBrand}
            className="fv-btn-ghost px-3 py-1.5 text-xs disabled:opacity-40"
          >
            Import from brand
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={handleExport}
            className="rounded-lg border border-[var(--fv-accent)]/40 bg-[var(--fv-accent-muted)] px-3 py-1.5 text-xs text-[var(--fv-accent)] hover:bg-[var(--fv-accent-muted)] disabled:opacity-50"
          >
            Export HTML
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs text-zinc-500">Presets</span>
        <div className="flex flex-wrap gap-2">
          {presets.map((p) => (
            <Swatch
              key={p.id}
              color={p.accent}
              label={p.name}
              active={palette.preset === p.preset}
              disabled={disabled}
              onClick={() => selectPreset(p)}
            />
          ))}
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={toggleMode}
          className="ml-auto rounded-lg border border-white/15 px-3 py-1.5 text-xs capitalize text-zinc-300 hover:bg-white/5 disabled:opacity-50"
        >
          {colorMode} mode
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <ColorField
          label="Accent"
          value={palette.accent}
          disabled={disabled}
          onChange={(v) => updateColor("accent", v)}
        />
        <ColorField
          label="Background"
          value={palette.background}
          disabled={disabled}
          onChange={(v) => updateColor("background", v)}
        />
        <ColorField
          label="Text"
          value={palette.foreground}
          disabled={disabled}
          onChange={(v) => updateColor("foreground", v)}
        />
      </div>
    </div>
  );
}
