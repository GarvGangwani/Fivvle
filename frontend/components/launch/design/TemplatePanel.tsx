"use client";

import { PAGE_TEMPLATES, type TemplateId } from "@/lib/templates";
import type { CopyJson, PageJson } from "@/lib/types";
import { buildPageForTemplatePreview } from "@/lib/template-preview-page";
import { DesignCollapsibleCard } from "./DesignCollapsibleCard";

type Props = {
  templateId: TemplateId;
  copy: CopyJson;
  page: PageJson;
  disabled?: boolean;
  onSelect: (templateId: TemplateId, nextPage: PageJson) => void;
};

export function TemplatePanel({
  templateId,
  copy,
  page,
  disabled,
  onSelect,
}: Props) {
  return (
    <DesignCollapsibleCard title="Template" defaultOpen>
      <p className="mb-3 font-mono text-mono-sm uppercase text-ink-primary/60">
        Pick a template — your copy stays the same.
      </p>
      <div className="grid grid-cols-2 gap-2">
        {PAGE_TEMPLATES.map((tpl) => {
          const active = tpl.id === templateId;
          return (
            <button
              key={tpl.id}
              type="button"
              disabled={disabled}
              onClick={() => {
                if (active) return;
                const next = buildPageForTemplatePreview(page, copy, tpl.id);
                onSelect(tpl.id, next);
              }}
              className={`relative border-2 border-border-master p-2 text-left transition-all disabled:opacity-50 ${
                active
                  ? "bg-brutalist-yellow shadow-brutal-sm"
                  : "bg-white hover:-translate-y-0.5 hover:shadow-brutal-sm"
              }`}
            >
              {active ? (
                <span className="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center border-2 border-border-master bg-ink-primary text-ink-inverse">
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 14 }}
                    aria-hidden="true"
                  >
                    check
                  </span>
                </span>
              ) : null}
              <div
                className="mb-2 h-14 w-full border-2 border-border-master"
                style={{
                  background: `linear-gradient(135deg, ${tpl.preview.accent} 0%, ${tpl.preview.bg} 55%)`,
                }}
                aria-hidden
              />
              <p className="font-label-sm text-label-sm uppercase tracking-wider text-ink-primary">
                {tpl.name}
              </p>
              {active ? (
                <p className="mt-0.5 font-mono text-mono-sm uppercase text-ink-primary/70">
                  Active
                </p>
              ) : null}
            </button>
          );
        })}
      </div>
    </DesignCollapsibleCard>
  );
}
