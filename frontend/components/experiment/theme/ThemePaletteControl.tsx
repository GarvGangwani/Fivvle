"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Palette } from "lucide-react";
import {
  DEFAULT_PALETTE_NAME,
  getThemePalette,
  isThemePaletteName,
  THEME_PALETTES,
  type ThemePaletteName,
} from "@/lib/theme-palettes";

type Props = {
  /** Active palette. Null or the default name both mean platform purple. */
  active: string | null;
  /** Palette the AI suggested at capture, if any. */
  suggested: string | null;
  onSelect: (palette: ThemePaletteName | null) => void;
  disabled?: boolean;
};

/** Both null and the default name render as "Default" — they look identical. */
function isDefaultSelection(active: string | null): boolean {
  return !isThemePaletteName(active) || active === DEFAULT_PALETTE_NAME;
}

export function ThemePaletteControl({
  active,
  suggested,
  onSelect,
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const defaultSelected = isDefaultSelection(active);
  const activePalette = getThemePalette(active);
  const suggestedPalette = isThemePaletteName(suggested)
    ? getThemePalette(suggested)
    : null;

  const choose = (palette: ThemePaletteName | null) => {
    setOpen(false);
    onSelect(palette);
  };

  return (
    <div ref={menuRef} className="absolute z-20" style={{ left: 64, bottom: 24 }}>
      {open ? (
        <div className="absolute bottom-full left-0 mb-0 w-[228px] rounded-md border-2 border-border-master bg-surface-card shadow-brutal-md">
          <p className="border-b-2 border-border-master px-3 py-2 font-mono text-mono-sm uppercase tracking-[0.14em] text-ink-tertiary">
            Canvas theme
          </p>

          <button
            type="button"
            onClick={() => choose(null)}
            className="flex w-full items-center gap-2 border-b-2 border-border-master px-3 py-2 text-left hover:bg-surface-muted"
          >
            <span
              aria-hidden
              className="h-4 w-4 shrink-0 border-2 border-border-master"
              style={{ backgroundColor: getThemePalette(null).accent }}
            />
            <span className="flex-1 font-label-md text-label-sm uppercase text-ink-primary">
              Default
            </span>
            {defaultSelected ? (
              <Check className="h-3.5 w-3.5 shrink-0" strokeWidth={3} aria-hidden />
            ) : null}
          </button>

          {suggestedPalette && suggestedPalette.name !== DEFAULT_PALETTE_NAME ? (
            <button
              type="button"
              onClick={() => choose(suggestedPalette.name)}
              className="flex w-full items-center gap-2 border-b-2 border-border-master px-3 py-2 text-left hover:bg-surface-muted"
            >
              <span
                aria-hidden
                className="h-4 w-4 shrink-0 border-2 border-border-master"
                style={{ backgroundColor: suggestedPalette.accent }}
              />
              <span className="min-w-0 flex-1">
                <span className="block font-label-md text-label-sm uppercase text-ink-primary">
                  AI-Suggested
                </span>
                <span className="block truncate font-mono text-mono-sm uppercase text-ink-tertiary">
                  {suggestedPalette.displayName}
                </span>
              </span>
              {active === suggestedPalette.name ? (
                <Check className="h-3.5 w-3.5 shrink-0" strokeWidth={3} aria-hidden />
              ) : null}
            </button>
          ) : null}

          <div className="flex flex-wrap gap-2 p-3" role="listbox" aria-label="Palettes">
            {THEME_PALETTES.map((palette) => {
              const selected =
                palette.name === DEFAULT_PALETTE_NAME
                  ? defaultSelected
                  : active === palette.name;
              return (
                <button
                  key={palette.name}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  title={`${palette.displayName} — ${palette.domain}`}
                  onClick={() =>
                    choose(
                      palette.name === DEFAULT_PALETTE_NAME ? null : palette.name,
                    )
                  }
                  className={`h-7 w-7 border-2 border-border-master transition-all ${
                    selected
                      ? "scale-110 shadow-brutal-sm ring-2 ring-ink-primary"
                      : "hover:scale-105"
                  }`}
                  style={{ backgroundColor: palette.accent }}
                />
              );
            })}
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled}
        className="flex h-[32px] w-[32px] items-center justify-center rounded-none border-2 border-border-master bg-surface-card text-ink-primary shadow-brutal-sm hover:shadow-brutal-md disabled:opacity-50"
        aria-label="Canvas theme"
        aria-expanded={open}
        title={`Canvas theme — ${activePalette.displayName}`}
      >
        <Palette className="h-4 w-4" style={{ color: activePalette.accent }} aria-hidden />
      </button>
    </div>
  );
}
