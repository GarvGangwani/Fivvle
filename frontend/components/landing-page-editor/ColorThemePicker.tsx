"use client";

import { useCallback, useRef, useState } from "react";
import { Moon, RotateCcw, Shuffle, Sun, Undo2 } from "lucide-react";
import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import {
  defaultPaletteForTemplate,
  extractColorsFromBrand,
  generateIntelligentPalette,
  getPresetsByMode,
  inferColorModeFromPalette,
  resolveColorPalette,
  type ColorMode,
  type UserColorPalette,
} from "@/lib/color-palettes";
import { downloadExportHtml } from "@/lib/export-page";

const HISTORY_LIMIT = 20;

export interface ThemePatch {
  color_mode?: ColorMode;
  color_palette?: Partial<UserColorPalette>;
}

interface PaletteSnapshot {
  color_mode?: ColorMode;
  color_palette: UserColorPalette;
}

interface ColorThemePickerProps {
  templateId: TemplateId;
  page: PageJson;
  copy: CopyJson;
  projectName: string;
  brandVisualDirection?: string;
  disabled?: boolean;
  showExport?: boolean;
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
        active
          ? "border-[var(--fv-accent)] scale-110"
          : "border-[var(--fv-border-strong)] hover:border-[color-mix(in_srgb,var(--fv-text)_28%,transparent)]"
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
      <span className="text-xs text-[var(--fv-text-muted)]">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="lp-color-picker-swatch h-9 w-9 cursor-pointer rounded border border-[var(--fv-border)] bg-[var(--fv-surface)] p-0.5 disabled:opacity-50"
        />
        <input
          type="text"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="lp-color-hex-input flex-1 disabled:opacity-50"
        />
      </div>
    </label>
  );
}

function PresetRow({
  label,
  presets,
  activePreset,
  disabled,
  onSelect,
}: {
  label: string;
  presets: Array<UserColorPalette & { id: string; name: string }>;
  activePreset: string;
  disabled?: boolean;
  onSelect: (preset: UserColorPalette & { id: string; name: string }) => void;
}) {
  return (
    <div className="space-y-2">
      <span className="text-xs text-[var(--fv-text-muted)]">{label}</span>
      <div className="flex flex-wrap gap-2">
        {presets.map((p) => (
          <Swatch
            key={p.id}
            color={p.accent}
            label={p.name}
            active={activePreset === p.preset}
            disabled={disabled}
            onClick={() => onSelect(p)}
          />
        ))}
      </div>
    </div>
  );
}

export function ColorThemePicker({
  templateId,
  page,
  copy,
  projectName,
  brandVisualDirection,
  disabled,
  showExport = true,
  onChange,
  onPersist,
}: ColorThemePickerProps) {
  const palette = resolveColorPalette(page, templateId);
  const { light: lightPresets, dark: darkPresets } = getPresetsByMode(templateId);
  const historyRef = useRef<PaletteSnapshot[]>([]);
  const [canUndo, setCanUndo] = useState(false);

  const commit = useCallback(
    (patch: ThemePatch) => {
      const mergedPalette = {
        ...palette,
        ...(patch.color_palette ?? {}),
      };
      const inferredMode = inferColorModeFromPalette(mergedPalette);
      const nextPage: PageJson = {
        ...page,
        color_mode: patch.color_mode ?? inferredMode,
        color_palette: mergedPalette,
      };
      const nextPatch = { ...patch, color_mode: nextPage.color_mode };
      onChange(nextPatch, nextPage);
      onPersist(nextPatch);
    },
    [onChange, onPersist, page, palette],
  );

  const apply = useCallback(
    (patch: ThemePatch, options?: { skipHistory?: boolean }) => {
      if (!options?.skipHistory) {
        historyRef.current.push({
          color_mode: page.color_mode,
          color_palette: { ...palette },
        });
        if (historyRef.current.length > HISTORY_LIMIT) {
          historyRef.current.shift();
        }
        setCanUndo(true);
      }
      commit(patch);
    },
    [commit, page.color_mode, palette],
  );

  const undo = () => {
    const previous = historyRef.current.pop();
    if (!previous) {
      setCanUndo(false);
      return;
    }
    setCanUndo(historyRef.current.length > 0);
    commit({
      color_mode: previous.color_mode ?? inferColorModeFromPalette(previous.color_palette),
      color_palette: previous.color_palette,
    });
  };

  const resetToDefault = () => {
    const defaults = defaultPaletteForTemplate(templateId);
    apply({
      color_mode: inferColorModeFromPalette(defaults),
      color_palette: defaults,
    });
  };

  const selectPreset = (preset: UserColorPalette & { id?: string }) => {
    apply({
      color_mode: inferColorModeFromPalette(preset),
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

  const shufflePalette = (mode: ColorMode) => {
    const generated = generateIntelligentPalette(templateId, mode);
    apply({ color_mode: mode, color_palette: generated });
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
            disabled={disabled || !canUndo}
            onClick={undo}
            title="Undo last color change"
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs disabled:opacity-40"
          >
            <Undo2 className="h-3.5 w-3.5" strokeWidth={2.25} />
            Undo
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={resetToDefault}
            title="Reset to template default colors"
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs disabled:opacity-40"
          >
            <RotateCcw className="h-3.5 w-3.5" strokeWidth={2.25} />
            Reset
          </button>
          {brandVisualDirection?.trim() ? (
            <button
              type="button"
              disabled={disabled}
              onClick={importFromBrand}
              className="fv-btn-ghost px-3 py-1.5 text-xs disabled:opacity-40"
            >
              Import from brand
            </button>
          ) : null}
          {showExport ? (
            <button
              type="button"
              disabled={disabled}
              onClick={handleExport}
              className="rounded-lg border border-[var(--fv-accent)]/40 bg-[var(--fv-accent-muted)] px-3 py-1.5 text-xs text-[var(--fv-accent)] hover:bg-[var(--fv-accent-muted)] disabled:opacity-50"
            >
              Export HTML
            </button>
          ) : null}
        </div>
      </div>

      <div className="space-y-3">
        <PresetRow
          label="Light presets"
          presets={lightPresets}
          activePreset={palette.preset}
          disabled={disabled}
          onSelect={selectPreset}
        />
        <PresetRow
          label="Dark presets"
          presets={darkPresets}
          activePreset={palette.preset}
          disabled={disabled}
          onSelect={selectPreset}
        />
        <div className="flex flex-wrap justify-end gap-2 pt-1">
          <button
            type="button"
            disabled={disabled}
            onClick={() => shufflePalette("light")}
            title="Generate a harmonious light palette"
            className="lp-color-random-btn"
          >
            <Shuffle className="h-3.5 w-3.5" strokeWidth={2.25} />
            <Sun className="h-3 w-3" strokeWidth={2.25} />
            Light
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => shufflePalette("dark")}
            title="Generate a harmonious dark palette"
            className="lp-color-random-btn"
          >
            <Shuffle className="h-3.5 w-3.5" strokeWidth={2.25} />
            <Moon className="h-3 w-3" strokeWidth={2.25} />
            Dark
          </button>
        </div>
      </div>

      <div className="grid gap-3">
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
