"use client";

import type { PageJson } from "@/lib/types";
import {
  GRADIENT_STYLES,
  SURFACE_TEXTURES,
  formatHeroGlowLabel,
  resolveSurface,
  type GradientStyle,
  type SurfaceTexture,
} from "@/lib/surface";
import { mergeSurfacePatch } from "@/components/landing-templates/SurfaceShell";
import { DesignCollapsibleCard } from "./DesignCollapsibleCard";
import { BrutalistSlider } from "./BrutalistSlider";

type Props = {
  page: PageJson;
  disabled?: boolean;
  onChange: (nextPage: PageJson) => void;
};

export function SurfaceAtmospherePanel({ page, disabled, onChange }: Props) {
  const surface = resolveSurface(page);
  const textureEnabled = surface.texture !== "none";
  const gradientEnabled = surface.gradient_style !== "flat";

  const apply = (patch: Parameters<typeof mergeSurfacePatch>[1]) => {
    // Never write deprecated hero_glow — intensity only.
    const cleaned = { ...patch };
    delete cleaned.hero_glow;
    onChange(mergeSurfacePatch(page, cleaned));
  };

  return (
    <DesignCollapsibleCard title="Surface & atmosphere" defaultOpen={false}>
      <div className="flex flex-col gap-5">
        <div>
          <p className="font-label-sm text-label-sm uppercase tracking-wider text-ink-primary">
            Background texture
          </p>
          <p className="mt-0.5 font-mono text-mono-sm uppercase text-ink-primary/50">
            Pick a surface style, then dial intensity below.
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {SURFACE_TEXTURES.map((t) => (
              <OptionChip
                key={t.id}
                label={t.label}
                active={surface.texture === t.id}
                disabled={disabled}
                onClick={() => apply({ texture: t.id as SurfaceTexture })}
              />
            ))}
          </div>
          <div className="mt-3">
            <BrutalistSlider
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
          <p className="font-label-sm text-label-sm uppercase tracking-wider text-ink-primary">
            Gradient style
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {GRADIENT_STYLES.map((g) => (
              <OptionChip
                key={g.id}
                label={g.label}
                active={surface.gradient_style === g.id}
                disabled={disabled}
                onClick={() =>
                  apply({ gradient_style: g.id as GradientStyle })
                }
              />
            ))}
          </div>
          <div className="mt-3">
            <BrutalistSlider
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

        <BrutalistSlider
          label="Hero glow"
          hint="Accent spotlight behind the hero — 0% is off"
          value={surface.hero_glow_intensity}
          disabled={disabled}
          formatValue={(v) => formatHeroGlowLabel(v)}
          onChange={(hero_glow_intensity) =>
            apply({ hero_glow_intensity })
          }
        />
      </div>
    </DesignCollapsibleCard>
  );
}

function OptionChip({
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
      className={`border-2 border-border-master px-2.5 py-1.5 font-label-sm text-label-sm uppercase tracking-wider transition-all disabled:opacity-50 ${
        active
          ? "bg-brutalist-yellow text-ink-primary shadow-brutal-sm"
          : "bg-white text-ink-primary hover:-translate-y-0.5"
      }`}
    >
      {label}
    </button>
  );
}
