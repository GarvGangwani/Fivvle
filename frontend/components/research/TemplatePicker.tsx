"use client";

import { Loader2, Sparkles } from "lucide-react";
import { PAGE_TEMPLATES, type TemplateId } from "@/lib/templates";
import { TemplatePreviewThumb } from "@/components/landing-page-editor/TemplatePreviewThumb";
import {
  TEMPLATE_PICKER_DUMMY_COPY,
  TEMPLATE_PICKER_DUMMY_PAGE,
} from "@/lib/template-preview-page";

export type { TemplateId };

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
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PAGE_TEMPLATES.map((template) => {
          const selected = selectedId === template.id;
          return (
            <div
              key={template.id}
              role="radio"
              tabIndex={0}
              aria-checked={selected}
              onClick={() => onSelect(template.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(template.id);
                }
              }}
              className={`group cursor-pointer overflow-hidden rounded-xl border text-left transition-all duration-200 ${
                selected
                  ? "border-[var(--fv-accent)] ring-2 ring-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]"
                  : "border-[var(--fv-border)] hover:border-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]"
              }`}
            >
              <TemplatePreviewThumb
                templateId={template.id}
                copy={TEMPLATE_PICKER_DUMMY_COPY}
                page={TEMPLATE_PICKER_DUMMY_PAGE}
                projectName="Your startup"
              />
              <div className="border-t border-[var(--fv-border)] bg-[var(--fv-surface-2)] p-4">
                <p className="font-semibold text-[var(--fv-text)]">
                  {template.name}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                  {template.description}
                </p>
                {selected && (
                  <p className="mt-2 text-[10px] font-bold uppercase text-[var(--fv-accent)]">
                    Selected
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={onGenerate}
        disabled={!selectedId || generating}
        className="fv-btn-primary inline-flex w-full items-center justify-center gap-2 py-3 text-sm disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:px-8"
      >
        {generating ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Starting generation…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Generate landing page
          </>
        )}
      </button>
    </div>
  );
}
