"use client";

import { REGENERATABLE_SECTIONS } from "@/lib/types";
import { RegenerateButton } from "./RegenerateButton";

interface SectionEditorProps {
  onRegenerate: (sectionType: string) => void;
  onRegenerateAll: () => void;
  regeneratingSection: string | null;
  isRegeneratingAll: boolean;
  version: number;
}

export function SectionEditor({
  onRegenerate,
  onRegenerateAll,
  regeneratingSection,
  isRegeneratingAll,
  version,
}: SectionEditorProps) {
  return (
    <aside className="fv-card space-y-6 p-6">
      <div>
        <h3 className="text-lg font-semibold text-white">Regenerate</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Each action creates a new output version (v{version}).
        </p>
      </div>

      <button
        type="button"
        disabled={isRegeneratingAll || !!regeneratingSection}
        onClick={onRegenerateAll}
        className="fv-btn-primary w-full justify-center py-2.5 text-sm disabled:opacity-50"
      >
        {isRegeneratingAll ? "Regenerating page…" : "Regenerate entire page"}
      </button>

      <div className="flex flex-wrap gap-2">
        {REGENERATABLE_SECTIONS.map((section) => (
          <RegenerateButton
            key={section}
            sectionType={section}
            label={section}
            onRegenerate={onRegenerate}
            isLoading={regeneratingSection === section}
          />
        ))}
      </div>
    </aside>
  );
}
