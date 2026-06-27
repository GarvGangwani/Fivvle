import type { PageJson, PageSurface, GradientStyle, HeroGlow, SurfaceTexture } from "./types";



export type { PageSurface, GradientStyle, HeroGlow, SurfaceTexture } from "./types";



export const SURFACE_TEXTURES: {

  id: SurfaceTexture;

  label: string;

  description: string;

}[] = [

  { id: "none", label: "Clean", description: "Flat background" },

  { id: "grain", label: "Grain", description: "Subtle film noise" },

  { id: "paper", label: "Paper", description: "Soft paper fibers" },

  { id: "dot-grid", label: "Dot grid", description: "Light technical grid" },

  { id: "linen", label: "Linen", description: "Woven fabric texture" },

];



export const GRADIENT_STYLES: { id: GradientStyle; label: string }[] = [

  { id: "flat", label: "Flat" },

  { id: "radial", label: "Radial" },

  { id: "mesh-warm", label: "Warm mesh" },

  { id: "mesh-cool", label: "Cool mesh" },

];



const LEGACY_HERO_GLOW_INTENSITY: Record<HeroGlow, number> = {

  off: 0,

  soft: 42,

  bold: 88,

};



export interface ResolvedPageSurface {

  texture: SurfaceTexture;

  gradient_style: GradientStyle;

  hero_glow_intensity: number;

  texture_intensity: number;

  gradient_intensity: number;

}



export const DEFAULT_SURFACE: ResolvedPageSurface = {

  texture: "none",

  hero_glow_intensity: 0,

  gradient_style: "flat",

  texture_intensity: 55,

  gradient_intensity: 72,

};



export function clampIntensity(

  value: number | undefined,

  fallback: number,

): number {

  if (value == null || Number.isNaN(value)) return fallback;

  return Math.min(100, Math.max(0, Math.round(value)));

}



function resolveHeroGlowIntensity(surface: PageSurface | undefined): number {

  if (surface?.hero_glow_intensity != null) {

    return clampIntensity(surface.hero_glow_intensity, DEFAULT_SURFACE.hero_glow_intensity);

  }

  if (surface?.hero_glow) {

    return LEGACY_HERO_GLOW_INTENSITY[surface.hero_glow] ?? 0;

  }

  return DEFAULT_SURFACE.hero_glow_intensity;

}



export function resolveSurface(page: PageJson | undefined): ResolvedPageSurface {

  const s = page?.surface;

  return {

    texture: s?.texture ?? DEFAULT_SURFACE.texture,

    gradient_style: s?.gradient_style ?? DEFAULT_SURFACE.gradient_style,

    hero_glow_intensity: resolveHeroGlowIntensity(s),

    texture_intensity: clampIntensity(

      s?.texture_intensity,

      DEFAULT_SURFACE.texture_intensity,

    ),

    gradient_intensity: clampIntensity(

      s?.gradient_intensity,

      DEFAULT_SURFACE.gradient_intensity,

    ),

  };

}



export function defaultSurfaceForTemplate(_templateId: string): PageSurface {

  return { ...DEFAULT_SURFACE };

}



export function formatHeroGlowLabel(intensity: number): string {

  if (intensity <= 0) return "Off";

  if (intensity < 35) return "Subtle";

  if (intensity < 70) return "Medium";

  return "Strong";

}



export function formatSurfaceSummary(surface: ResolvedPageSurface): string {

  const textureLabel =

    surface.texture === "none"

      ? "Clean"

      : `${SURFACE_TEXTURES.find((t) => t.id === surface.texture)?.label ?? surface.texture} ${surface.texture_intensity}%`;

  const gradientLabel =

    surface.gradient_style === "flat"

      ? "Flat"

      : `${GRADIENT_STYLES.find((g) => g.id === surface.gradient_style)?.label ?? surface.gradient_style} ${surface.gradient_intensity}%`;

  return `${textureLabel} · ${formatHeroGlowLabel(surface.hero_glow_intensity)} glow · ${gradientLabel}`;

}


