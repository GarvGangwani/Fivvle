"use client";

export const TEMPLATE_OPTIONS = [
  {
    id: "dark-premium",
    name: "Dark Premium",
    description: "Sleek, technical — dev tools, AI products",
    accent: "#06B6D4",
  },
  {
    id: "bold-v1",
    name: "Bold V1",
    description: "Energetic, modern — consumer, design-forward",
    accent: "#EF4444",
  },
  {
    id: "minimal-v3",
    name: "Minimal V3",
    description: "Confident, understated — B2B SaaS, productivity",
    accent: "#10B981",
  },
  {
    id: "editorial-saas",
    name: "Editorial SaaS",
    description: "Thoughtful, narrative — content-first",
    accent: "#F59E0B",
  },
  {
    id: "aether",
    name: "Aether",
    description: "Ethereal, innovative — future-forward products",
    accent: "#8B5CF6",
  },
  {
    id: "abstract",
    name: "Abstract",
    description: "Creative, artistic — design-led brands",
    accent: "#EC4899",
  },
] as const;

export type TemplateId = (typeof TEMPLATE_OPTIONS)[number]["id"];

interface TemplatePickerProps {
  selectedId: TemplateId | null;
  onSelect: (id: TemplateId) => void;
  onGenerate: () => void;
  generating?: boolean;
}

export function TemplatePicker({
  selectedId,
  onSelect,
  onGenerate,
  generating = false,
}: TemplatePickerProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-[16px] font-bold text-[var(--fv-text)]">
          Choose a template for your landing page
        </h2>
        <p className="mt-1 text-[14px] text-[var(--fv-text-muted)]">
          Select the style that best fits your product
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {TEMPLATE_OPTIONS.map((template) => (
          <button
            key={template.id}
            type="button"
            onClick={() => onSelect(template.id)}
            className={`host-card fv-card-hover text-left ${
              selectedId === template.id ? "host-card selected fv-card-selected" : ""
            }`}
          >
            <div
              className="h-1 w-full"
              style={{ background: template.accent }}
            />
            <div className="p-4">
              <p className="text-[14px] font-semibold text-[#CBD5E1]">
                {template.name}
              </p>
              <p className="mt-1 text-[12px] text-[var(--fv-text-muted)]">
                {template.description}
              </p>
            </div>
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={onGenerate}
        disabled={!selectedId || generating}
        className="fv-btn-primary host-btn justify-center py-3 text-sm disabled:cursor-not-allowed"
      >
        {generating ? "Starting generation…" : "Generate Landing Page"}
      </button>
    </div>
  );
}
