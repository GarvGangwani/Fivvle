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

/** Lightweight tinted wireframe — palette only, no TemplateRenderer / lp-* CSS. */
function TemplateMiniMock({
  bg,
  accent,
  text,
}: {
  bg: string;
  accent: string;
  text: string;
}) {
  const muted = `${text}99`;
  return (
    <div
      className="mb-2 flex aspect-[16/10] w-full flex-col overflow-hidden border-2 border-border-master p-1.5"
      style={{ backgroundColor: bg }}
      aria-hidden
    >
      {/* Header bar */}
      <div className="mb-1.5 flex items-center gap-1">
        <div
          className="h-1 w-4 shrink-0"
          style={{ backgroundColor: accent }}
        />
        <div
          className="h-0.5 flex-1"
          style={{ backgroundColor: muted }}
        />
      </div>
      {/* Heading block */}
      <div
        className="mb-1 h-2 w-3/4"
        style={{ backgroundColor: text }}
      />
      <div
        className="mb-1.5 h-1.5 w-1/2"
        style={{ backgroundColor: text }}
      />
      {/* Body lines */}
      <div
        className="mb-0.5 h-0.5 w-full"
        style={{ backgroundColor: muted }}
      />
      <div
        className="mb-auto h-0.5 w-4/5"
        style={{ backgroundColor: muted }}
      />
      {/* CTA */}
      <div
        className="mt-1.5 h-2 w-8 self-start"
        style={{ backgroundColor: accent }}
      />
    </div>
  );
}

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
          const { bg, accent, text } = tpl.preview;
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
                  : "bg-surface-elevated hover:-translate-y-0.5 hover:shadow-brutal-sm"
              }`}
            >
              {active ? (
                <span className="absolute right-1.5 top-1.5 z-10 flex h-5 w-5 items-center justify-center border-2 border-border-master bg-ink-primary text-ink-inverse">
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 14 }}
                    aria-hidden="true"
                  >
                    check
                  </span>
                </span>
              ) : null}
              <TemplateMiniMock bg={bg} accent={accent} text={text} />
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
