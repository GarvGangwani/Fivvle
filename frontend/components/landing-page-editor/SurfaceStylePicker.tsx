"use client";

import type { PageJson } from "@/lib/types";
import {
  GRADIENT_STYLES,
  SURFACE_TEXTURES,
  formatHeroGlowLabel,
  resolveSurface,
  type GradientStyle,
  type PageSurface,
  type SurfaceTexture,
} from "@/lib/surface";
import { mergeSurfacePatch } from "@/components/landing-templates/SurfaceShell";
import { DesignSlider } from "./DesignSlider";

interface SurfaceStylePickerProps {
  page: PageJson;
  disabled?: boolean;
  onChange: (nextPage: PageJson) => void;
}

function OptionPill({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition-colors disabled:opacity-50 ${
        active
          ? "border-[var(--fv-accent)]/50 bg-[var(--fv-accent-muted)] text-[var(--fv-accent)]"
          : "border-[var(--fv-border)] text-[var(--fv-text-soft)] hover:border-[var(--fv-border-strong)]"
      }`}
    >
      {label}
    </button>
  );
}

export function SurfaceStylePicker({
  page,
  disabled,
  onChange,
}: SurfaceStylePickerProps) {
  const surface = resolveSurface(page);

  const apply = (patch: Partial<PageSurface>) => {
    onChange(mergeSurfacePatch(page, patch));
  };

  const textureEnabled = surface.texture !== "none";
  const gradientEnabled = surface.gradient_style !== "flat";

  return (
    <div className="space-y-5">
      <div>
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
          Background texture
        </p>
        <p className="mt-1 text-[12px] text-[var(--fv-text-dim)]">
          Pick a surface style, then dial intensity below.
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SURFACE_TEXTURES.map((t) => (
            <OptionPill
              key={t.id}
              label={t.label}
              active={surface.texture === t.id}
              disabled={disabled}
              onClick={() => apply({ texture: t.id as SurfaceTexture })}
            />
          ))}
        </div>
        <div className="mt-3">
          <DesignSlider
            label="Texture intensity"
            hint={
              textureEnabled
                ? "How visible the background texture appears"
                : "Choose a texture other than Clean to adjust"
            }
            value={surface.texture_intensity}
            disabled={disabled || !textureEnabled}
            onChange={(texture_intensity) => apply({ texture_intensity })}
          />
        </div>
      </div>

      <div>
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
          Gradient style
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {GRADIENT_STYLES.map((g) => (
            <OptionPill
              key={g.id}
              label={g.label}
              active={surface.gradient_style === g.id}
              disabled={disabled}
              onClick={() => apply({ gradient_style: g.id as GradientStyle })}
            />
          ))}
        </div>
        <div className="mt-3">
          <DesignSlider
            label="Gradient intensity"
            hint={
              gradientEnabled
                ? "Strength of the background color wash"
                : "Choose Radial or mesh to adjust"
            }
            value={surface.gradient_intensity}
            disabled={disabled || !gradientEnabled}
            onChange={(gradient_intensity) => apply({ gradient_intensity })}
          />
        </div>
      </div>

      <DesignSlider
        label="Hero glow"
        hint="Accent spotlight behind the hero — 0% is off"
        value={surface.hero_glow_intensity}
        disabled={disabled}
        formatValue={(v) => formatHeroGlowLabel(v)}
        onChange={(hero_glow_intensity) =>
          apply({ hero_glow_intensity, hero_glow: undefined })
        }
      />
    </div>
  );
}
