"use client";

import { PAGE_TEMPLATES, type TemplateId } from "@/lib/templates";

interface ThemePickerProps {
  selected: TemplateId;
  onSelect: (id: TemplateId) => void;
  disabled?: boolean;
}

export function ThemePicker({ selected, onSelect, disabled }: ThemePickerProps) {
  return (
    <div className="space-y-3">
      <p className="fv-panel-label">
        Design template
      </p>
      <div className="grid gap-2">
        {PAGE_TEMPLATES.map((tpl) => {
          const active = selected === tpl.id;
          return (
            <button
              key={tpl.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(tpl.id)}
              className={`overflow-hidden rounded-xl border text-left transition-all disabled:opacity-50 ${
                active
                  ? "border-[var(--fv-accent)] ring-2 ring-[var(--fv-accent)]/30"
                  : "border-white/10 hover:border-white/25"
              }`}
            >
              <div
                className="flex h-16 items-end gap-2 p-3"
                style={{ background: tpl.preview.bg }}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: tpl.preview.accent }}
                />
                <span
                  className="mb-0.5 text-[10px] font-bold uppercase tracking-wider"
                  style={{ color: tpl.preview.text }}
                >
                  Aa
                </span>
              </div>
              <div className="space-y-1 bg-zinc-950/80 p-3">
                <p className="text-sm font-semibold text-white">{tpl.name}</p>
                <p className="text-xs text-zinc-500">{tpl.description}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
