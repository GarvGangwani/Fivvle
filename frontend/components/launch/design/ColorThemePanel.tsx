"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import {
  defaultPaletteForTemplate,
  getPresetsByMode,
  inferColorModeFromPalette,
  resolveColorPalette,
  type ColorMode,
  type ColorPreset,
  type UserColorPalette,
} from "@/lib/color-palettes";
import {
  applyColorModeToPage,
  applyColorPaletteToPage,
  normalizeHex,
  PALETTE_HISTORY_LIMIT,
  type PaletteHistoryEntry,
} from "@/lib/landing-design";
import { DesignCollapsibleCard } from "./DesignCollapsibleCard";

type Props = {
  templateId: TemplateId;
  page: PageJson;
  disabled?: boolean;
  onChange: (nextPage: PageJson) => void;
};

export function ColorThemePanel({
  templateId,
  page,
  disabled,
  onChange,
}: Props) {
  const palette = resolveColorPalette(page, templateId);
  const colorMode: ColorMode =
    page.color_mode ?? inferColorModeFromPalette(palette);
  const { light: lightPresets, dark: darkPresets } =
    getPresetsByMode(templateId);

  const historyRef = useRef<PaletteHistoryEntry[]>([]);
  const [canUndo, setCanUndo] = useState(false);

  const pushHistory = useCallback(() => {
    historyRef.current.push({
      color_mode: page.color_mode,
      color_palette: { ...palette },
    });
    if (historyRef.current.length > PALETTE_HISTORY_LIMIT) {
      historyRef.current.shift();
    }
    setCanUndo(true);
  }, [page.color_mode, palette]);

  const commitPalette = useCallback(
    (next: UserColorPalette, mode?: ColorMode, options?: { skipHistory?: boolean }) => {
      if (!options?.skipHistory) pushHistory();
      onChange(applyColorPaletteToPage(page, next, mode));
    },
    [onChange, page, pushHistory],
  );

  const undo = () => {
    const previous = historyRef.current.pop();
    if (!previous) {
      setCanUndo(false);
      return;
    }
    setCanUndo(historyRef.current.length > 0);
    onChange(
      applyColorPaletteToPage(
        page,
        previous.color_palette,
        previous.color_mode ??
          inferColorModeFromPalette(previous.color_palette),
      ),
    );
  };

  const reset = () => {
    const defaults = defaultPaletteForTemplate(templateId);
    commitPalette(defaults, inferColorModeFromPalette(defaults));
  };

  const selectPreset = (preset: ColorPreset) => {
    commitPalette(
      {
        preset: preset.preset,
        accent: preset.accent,
        background: preset.background,
        foreground: preset.foreground,
      },
      inferColorModeFromPalette(preset),
    );
  };

  const setModeOnly = (mode: ColorMode) => {
    if (mode === colorMode) return;
    pushHistory();
    onChange(applyColorModeToPage(page, mode));
  };

  const updateHex = (key: "accent" | "background" | "foreground", raw: string) => {
    const hex = normalizeHex(raw);
    if (!hex) return;
    commitPalette({
      ...palette,
      preset: "custom",
      [key]: hex,
    });
  };

  const headerActions = (
    <>
      <button
        type="button"
        disabled={disabled || !canUndo}
        onClick={undo}
        className="border-2 border-border-master bg-surface-elevated px-2 py-1 font-label-sm text-label-sm uppercase tracking-wider disabled:opacity-40"
      >
        Undo
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={reset}
        className="border-2 border-border-master bg-surface-elevated px-2 py-1 font-label-sm text-label-sm uppercase tracking-wider disabled:opacity-40"
      >
        Reset
      </button>
    </>
  );

  return (
    <DesignCollapsibleCard
      title="Color theme"
      defaultOpen
      headerActions={headerActions}
    >
      <div className="flex flex-col gap-4">
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

        <div>
          <p className="mb-1.5 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/60">
            Mode
          </p>
          <div className="flex gap-1">
            {(["light", "dark"] as const).map((mode) => {
              const active = colorMode === mode;
              return (
                <button
                  key={mode}
                  type="button"
                  disabled={disabled}
                  onClick={() => setModeOnly(mode)}
                  className={`flex-1 border-2 border-border-master px-2 py-1.5 font-label-sm text-label-sm uppercase tracking-wider transition-all disabled:opacity-50 ${
                    active
                      ? "bg-brutalist-yellow text-ink-primary shadow-brutal-sm"
                      : "bg-surface-elevated text-ink-primary hover:-translate-y-0.5"
                  }`}
                >
                  {mode}
                </button>
              );
            })}
          </div>
        </div>

        <HexField
          label="Accent"
          value={palette.accent}
          disabled={disabled}
          onCommit={(v) => updateHex("accent", v)}
        />
        <HexField
          label="Background"
          value={palette.background}
          disabled={disabled}
          onCommit={(v) => updateHex("background", v)}
        />
        <HexField
          label="Text"
          value={palette.foreground}
          disabled={disabled}
          onCommit={(v) => updateHex("foreground", v)}
        />
      </div>
    </DesignCollapsibleCard>
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
  presets: ColorPreset[];
  activePreset: string;
  disabled?: boolean;
  onSelect: (preset: ColorPreset) => void;
}) {
  if (presets.length === 0) return null;
  return (
    <div>
      <p className="mb-1.5 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/60">
        {label}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => {
          const active = activePreset === p.preset;
          return (
            <button
              key={p.id}
              type="button"
              title={p.name}
              disabled={disabled}
              onClick={() => onSelect(p)}
              className={`h-8 w-8 border-2 border-border-master transition-all disabled:opacity-50 ${
                active
                  ? "scale-110 shadow-brutal-sm ring-2 ring-ink-primary"
                  : "hover:scale-105"
              }`}
              style={{ background: p.accent }}
            />
          );
        })}
      </div>
    </div>
  );
}

function HexField({
  label,
  value,
  disabled,
  onCommit,
}: {
  label: string;
  value: string;
  disabled?: boolean;
  onCommit: (raw: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) setDraft(value);
  }, [value, focused]);

  const shown = focused ? draft : value;
  const invalid =
    focused && normalizeHex(draft) === null && draft.trim().length > 0;

  return (
    <div>
      <p className="mb-1 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/60">
        {label}
      </p>
      <div className="flex items-center gap-2">
        <span
          className="h-9 w-9 shrink-0 border-2 border-border-master"
          style={{ background: normalizeHex(shown) ?? value }}
          aria-hidden
        />
        <input
          type="text"
          disabled={disabled}
          value={shown}
          spellCheck={false}
          onFocus={() => {
            setFocused(true);
            setDraft(value);
          }}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => {
            setFocused(false);
            const hex = normalizeHex(draft);
            if (hex) onCommit(hex);
            else setDraft(value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              (e.target as HTMLInputElement).blur();
            }
          }}
          className={`min-w-0 flex-1 border-2 border-border-master bg-surface-elevated px-2 py-1.5 font-mono text-body-sm uppercase outline-none focus:border-brand-primary disabled:opacity-50 ${
            invalid ? "border-status-critical" : ""
          }`}
        />
      </div>
    </div>
  );
}
