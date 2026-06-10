"use client";

import { useState } from "react";
import { ChevronDown, Plus, Trash2 } from "lucide-react";
import type { CopyJson, FaqItem, FeatureCopy } from "@/lib/types";

interface CopyFieldsEditorProps {
  copy: CopyJson;
  onChange: (copy: CopyJson) => void;
  disabled?: boolean;
}

const INPUT_CLASS =
  "fv-input w-full rounded-xl border border-[var(--fv-border)] bg-white/[0.03] px-4 py-3 text-[14px] transition-all duration-200";
const TEXTAREA_CLASS = `${INPUT_CLASS} min-h-[100px] resize-y leading-relaxed`;

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="mb-1.5 block text-[13px] font-medium text-[var(--fv-text-soft)]">
      {children}
    </span>
  );
}

function AccordionSection({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-[var(--fv-border)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between py-3 transition-all duration-200 hover:text-[var(--fv-text)]"
        aria-expanded={open}
      >
        <span className="text-[14px] font-semibold text-[var(--fv-text)]">
          {title}
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-[var(--fv-text-muted)] transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`grid transition-all duration-200 ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <div className="space-y-3 pb-4">{children}</div>
        </div>
      </div>
    </div>
  );
}

function NestedItemCard({
  title,
  onRemove,
  disabled,
  children,
}: {
  title: string;
  onRemove: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="group space-y-3 rounded-xl border border-[var(--fv-border)] bg-white/[0.02] p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-medium text-[var(--fv-text-soft)]">
          {title}
        </span>
        <button
          type="button"
          disabled={disabled}
          onClick={onRemove}
          className="rounded-lg p-1.5 text-[var(--fv-danger)] opacity-0 transition-all duration-200 hover:bg-white/[0.05] group-hover:opacity-100 disabled:opacity-0"
          aria-label={`Remove ${title}`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {children}
    </div>
  );
}

function AddItemButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--fv-border-strong)] py-3 text-[13px] font-medium text-[var(--fv-text-soft)] transition-all duration-200 hover:border-[var(--fv-accent)] hover:text-[var(--fv-accent)] disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Plus className="h-4 w-4" />
      {label}
    </button>
  );
}

export function CopyFieldsEditor({
  copy,
  onChange,
  disabled,
}: CopyFieldsEditorProps) {
  const hero = copy.hero ?? { headline: "", subheadline: "", cta: "" };
  const problem = copy.problem ?? { heading: "", body: "" };
  const features = copy.features ?? [];
  const comparison = copy.comparison ?? {
    metric_label: "",
    competitor_name: "",
    our_features: [],
    competitor_features: [],
  };
  const proof = copy.proof ?? { headline: "", elements: [] };
  const faq = copy.faq ?? [];
  const objections = (copy.objections ?? {
    heading: "",
    items: [],
  }) as { heading: string; items: FaqItem[] };
  const cta = copy.cta ?? { heading: "", subheading: "", button: "" };

  function updateHero(field: keyof typeof hero, value: string) {
    onChange({ ...copy, hero: { ...hero, [field]: value } });
  }

  function updateFeature(index: number, field: keyof FeatureCopy, value: string) {
    const next = features.map((f, i) =>
      i === index ? { ...f, [field]: value } : f,
    );
    onChange({ ...copy, features: next });
  }

  function addFeature() {
    onChange({
      ...copy,
      features: [...features, { title: "", description: "" }],
    });
  }

  function removeFeature(index: number) {
    onChange({
      ...copy,
      features: features.filter((_, i) => i !== index),
    });
  }

  function updateFaq(index: number, field: keyof FaqItem, value: string) {
    const next = faq.map((item, i) =>
      i === index ? { ...item, [field]: value } : item,
    );
    onChange({ ...copy, faq: next });
  }

  function addFaq() {
    onChange({ ...copy, faq: [...faq, { question: "", answer: "" }] });
  }

  function removeFaq(index: number) {
    onChange({ ...copy, faq: faq.filter((_, i) => i !== index) });
  }

  function updateObjection(index: number, field: keyof FaqItem, value: string) {
    const next = objections.items.map((item, i) =>
      i === index ? { ...item, [field]: value } : item,
    );
    onChange({ ...copy, objections: { ...objections, items: next } });
  }

  function addObjection() {
    onChange({
      ...copy,
      objections: {
        ...objections,
        items: [...objections.items, { question: "", answer: "" }],
      },
    });
  }

  function removeObjection(index: number) {
    onChange({
      ...copy,
      objections: {
        ...objections,
        items: objections.items.filter((_, i) => i !== index),
      },
    });
  }

  const ourFeaturesText = (comparison.our_features ?? []).join("\n");
  const competitorFeaturesText = (comparison.competitor_features ?? []).join(
    "\n",
  );
  const proofElementsText = (proof.elements ?? []).join("\n");

  return (
    <div className="space-y-2">
      <AccordionSection title="Hero">
        <label className="block">
          <FieldLabel>Headline</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={hero.headline}
            onChange={(e) => updateHero("headline", e.target.value)}
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Subheadline</FieldLabel>
          <textarea
            disabled={disabled}
            value={hero.subheadline}
            onChange={(e) => updateHero("subheadline", e.target.value)}
            className={TEXTAREA_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Button text</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={hero.cta}
            onChange={(e) => updateHero("cta", e.target.value)}
            className={INPUT_CLASS}
          />
        </label>
      </AccordionSection>

      <AccordionSection title="Problem">
        <label className="block">
          <FieldLabel>Heading</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={problem.heading}
            onChange={(e) =>
              onChange({
                ...copy,
                problem: { ...problem, heading: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Body</FieldLabel>
          <textarea
            disabled={disabled}
            value={problem.body}
            onChange={(e) =>
              onChange({
                ...copy,
                problem: { ...problem, body: e.target.value },
              })
            }
            className={TEXTAREA_CLASS}
          />
        </label>
      </AccordionSection>

      <AccordionSection title="Features">
        {features.map((feature, index) => (
          <NestedItemCard
            key={index}
            title={`Feature ${index + 1}`}
            disabled={disabled}
            onRemove={() => removeFeature(index)}
          >
            <input
              type="text"
              disabled={disabled}
              value={feature.title}
              onChange={(e) => updateFeature(index, "title", e.target.value)}
              placeholder="Title"
              className={INPUT_CLASS}
            />
            <textarea
              disabled={disabled}
              value={feature.description}
              onChange={(e) =>
                updateFeature(index, "description", e.target.value)
              }
              placeholder="Description"
              className={TEXTAREA_CLASS}
            />
          </NestedItemCard>
        ))}
        <AddItemButton
          label="Add feature"
          disabled={disabled}
          onClick={addFeature}
        />
      </AccordionSection>

      <AccordionSection title="Comparison">
        <label className="block">
          <FieldLabel>Metric label</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={comparison.metric_label}
            onChange={(e) =>
              onChange({
                ...copy,
                comparison: { ...comparison, metric_label: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Competitor name</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={comparison.competitor_name}
            onChange={(e) =>
              onChange({
                ...copy,
                comparison: { ...comparison, competitor_name: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Our features (one per line)</FieldLabel>
          <textarea
            disabled={disabled}
            value={ourFeaturesText}
            onChange={(e) =>
              onChange({
                ...copy,
                comparison: {
                  ...comparison,
                  our_features: e.target.value
                    .split("\n")
                    .map((line) => line.trim())
                    .filter(Boolean),
                },
              })
            }
            className={TEXTAREA_CLASS}
          />
          <p className="mt-1 text-[12px] text-[var(--fv-text-dim)]">
            Enter one feature per line
          </p>
        </label>
        <label className="block">
          <FieldLabel>Competitor features (one per line)</FieldLabel>
          <textarea
            disabled={disabled}
            value={competitorFeaturesText}
            onChange={(e) =>
              onChange({
                ...copy,
                comparison: {
                  ...comparison,
                  competitor_features: e.target.value
                    .split("\n")
                    .map((line) => line.trim())
                    .filter(Boolean),
                },
              })
            }
            className={TEXTAREA_CLASS}
          />
          <p className="mt-1 text-[12px] text-[var(--fv-text-dim)]">
            Enter one feature per line
          </p>
        </label>
      </AccordionSection>

      <AccordionSection title="Proof">
        <label className="block">
          <FieldLabel>Headline</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={proof.headline}
            onChange={(e) =>
              onChange({
                ...copy,
                proof: { ...proof, headline: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Proof points (one per line)</FieldLabel>
          <textarea
            disabled={disabled}
            value={proofElementsText}
            onChange={(e) =>
              onChange({
                ...copy,
                proof: {
                  ...proof,
                  elements: e.target.value
                    .split("\n")
                    .map((line) => line.trim())
                    .filter(Boolean),
                },
              })
            }
            className={TEXTAREA_CLASS}
          />
          <p className="mt-1 text-[12px] text-[var(--fv-text-dim)]">
            Enter one proof point per line
          </p>
        </label>
      </AccordionSection>

      <AccordionSection title="Objections">
        <label className="block">
          <FieldLabel>Section heading</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={objections.heading}
            onChange={(e) =>
              onChange({
                ...copy,
                objections: { ...objections, heading: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
        {objections.items.map((item, index) => (
          <NestedItemCard
            key={index}
            title={`Objection ${index + 1}`}
            disabled={disabled}
            onRemove={() => removeObjection(index)}
          >
            <input
              type="text"
              disabled={disabled}
              value={item.question}
              onChange={(e) =>
                updateObjection(index, "question", e.target.value)
              }
              placeholder="Question"
              className={INPUT_CLASS}
            />
            <textarea
              disabled={disabled}
              value={item.answer}
              onChange={(e) => updateObjection(index, "answer", e.target.value)}
              placeholder="Answer"
              className={TEXTAREA_CLASS}
            />
          </NestedItemCard>
        ))}
        <AddItemButton
          label="Add objection"
          disabled={disabled}
          onClick={addObjection}
        />
      </AccordionSection>

      <AccordionSection title="FAQ">
        {faq.map((item, index) => (
          <NestedItemCard
            key={index}
            title={`Question ${index + 1}`}
            disabled={disabled}
            onRemove={() => removeFaq(index)}
          >
            <input
              type="text"
              disabled={disabled}
              value={item.question}
              onChange={(e) => updateFaq(index, "question", e.target.value)}
              placeholder="Question"
              className={INPUT_CLASS}
            />
            <textarea
              disabled={disabled}
              value={item.answer}
              onChange={(e) => updateFaq(index, "answer", e.target.value)}
              placeholder="Answer"
              className={TEXTAREA_CLASS}
            />
          </NestedItemCard>
        ))}
        <AddItemButton label="Add FAQ" disabled={disabled} onClick={addFaq} />
      </AccordionSection>

      <AccordionSection title="CTA">
        <label className="block">
          <FieldLabel>Heading</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={cta.heading}
            onChange={(e) =>
              onChange({
                ...copy,
                cta: { ...cta, heading: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Subheading</FieldLabel>
          <textarea
            disabled={disabled}
            value={cta.subheading}
            onChange={(e) =>
              onChange({
                ...copy,
                cta: { ...cta, subheading: e.target.value },
              })
            }
            className={TEXTAREA_CLASS}
          />
        </label>
        <label className="block">
          <FieldLabel>Button text</FieldLabel>
          <input
            type="text"
            disabled={disabled}
            value={cta.button}
            onChange={(e) =>
              onChange({
                ...copy,
                cta: { ...cta, button: e.target.value },
              })
            }
            className={INPUT_CLASS}
          />
        </label>
      </AccordionSection>
    </div>
  );
}
