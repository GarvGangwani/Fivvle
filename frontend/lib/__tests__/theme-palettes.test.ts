import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  DEFAULT_PALETTE_NAME,
  getThemePalette,
  isThemePaletteName,
  paletteAccentOverride,
  THEME_PALETTES,
} from "@/lib/theme-palettes";

describe("theme palettes", () => {
  it("exposes eight palettes with the default first", () => {
    expect(THEME_PALETTES).toHaveLength(8);
    expect(THEME_PALETTES[0]?.name).toBe(DEFAULT_PALETTE_NAME);
  });

  it("treats only curated names as valid", () => {
    expect(isThemePaletteName("emerald")).toBe(true);
    expect(isThemePaletteName("chartreuse")).toBe(false);
    expect(isThemePaletteName(null)).toBe(false);
  });

  it("falls back to the default palette for unknown names", () => {
    expect(getThemePalette("chartreuse").name).toBe(DEFAULT_PALETTE_NAME);
    expect(getThemePalette(null).accent).toBe("#7C3AED");
  });

  it("produces no override for the default so the canvas inherits :root", () => {
    expect(paletteAccentOverride(null)).toBeNull();
    expect(paletteAccentOverride(DEFAULT_PALETTE_NAME)).toBeNull();
    expect(paletteAccentOverride("chartreuse")).toBeNull();
  });

  it("maps a curated palette to accent token overrides", () => {
    expect(paletteAccentOverride("emerald")).toEqual({
      accent: "#047857",
      hover: "#065F46",
      muted: "rgba(4, 120, 87, 0.12)",
      fg: "#FFFFFF",
    });
  });
});

describe("backend palette parity", () => {
  /**
   * The table is mirrored by hand in Python and TypeScript, so drift is the
   * likeliest failure mode. Parse the backend source and compare values.
   */
  it("matches backend/app/services/idea_theme_palettes.py", () => {
    const source = readFileSync(
      path.resolve(
        process.cwd(),
        "..",
        "backend",
        "app",
        "services",
        "idea_theme_palettes.py",
      ),
      "utf8",
    );

    const backend = [
      ...source.matchAll(
        /ThemePalette\(\s*name="([^"]+)"[\s\S]*?accent="([^"]+)",\s*accent_hover="([^"]+)",\s*accent_muted="([^"]+)",\s*accent_fg="([^"]+)",/g,
      ),
    ];

    expect(backend).toHaveLength(THEME_PALETTES.length);

    for (const [, name, accent, hover, muted, fg] of backend) {
      const mirrored = getThemePalette(name);
      expect(mirrored.name).toBe(name);
      expect(mirrored.accent).toBe(accent);
      expect(mirrored.hover).toBe(hover);
      expect(mirrored.muted).toBe(muted);
      expect(mirrored.fg).toBe(fg);
    }
  });
});
