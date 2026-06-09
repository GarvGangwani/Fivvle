"use client";

import { Plus, Trash2 } from "lucide-react";
import type { CopyJson, FaqItem, FeatureCopy } from "@/lib/types";

interface CopyFieldsEditorProps {
  copy: CopyJson;
  onChange: (copy: CopyJson) => void;
  disabled?: boolean;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="text-[12px] font-semibold uppercase tracking-[0.06em]"
      style={{ color: "var(--fv-text-dim)" }}
    >
      {children}
    </span>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return <p className="fv-panel-label pt-2">{children}</p>;
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
    <div className="space-y-5">
      <SectionHeader>Hero</SectionHeader>
      <label className="block space-y-1.5">
        <FieldLabel>Headline</FieldLabel>
        <input
          type="text"
          disabled={disabled}
          value={hero.headline}
          onChange={(e) => updateHero("headline", e.target.value)}
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Subheadline</FieldLabel>
        <textarea
          disabled={disabled}
          rows={3}
          value={hero.subheadline}
          onChange={(e) => updateHero("subheadline", e.target.value)}
          className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Button text</FieldLabel>
        <input
          type="text"
          disabled={disabled}
          value={hero.cta}
          onChange={(e) => updateHero("cta", e.target.value)}
          className="fv-input px-3 py-2 text-sm"
        />
      </label>

      <SectionHeader>Problem</SectionHeader>
      <label className="block space-y-1.5">
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
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Body</FieldLabel>
        <textarea
          disabled={disabled}
          rows={4}
          value={problem.body}
          onChange={(e) =>
            onChange({
              ...copy,
              problem: { ...problem, body: e.target.value },
            })
          }
          className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
        />
      </label>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <SectionHeader>Features</SectionHeader>
          <button
            type="button"
            disabled={disabled}
            onClick={addFeature}
            className="icon-btn shrink-0"
            aria-label="Add feature"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        {features.map((feature, index) => (
          <div
            key={index}
            className="space-y-2 rounded-xl border border-[var(--fv-border)] p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <FieldLabel>Feature {index + 1}</FieldLabel>
              <button
                type="button"
                disabled={disabled}
                onClick={() => removeFeature(index)}
                className="icon-btn shrink-0"
                aria-label="Remove feature"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
            <input
              type="text"
              disabled={disabled}
              value={feature.title}
              onChange={(e) => updateFeature(index, "title", e.target.value)}
              placeholder="Title"
              className="fv-input px-3 py-2 text-sm"
            />
            <textarea
              disabled={disabled}
              rows={2}
              value={feature.description}
              onChange={(e) =>
                updateFeature(index, "description", e.target.value)
              }
              placeholder="Description"
              className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
            />
          </div>
        ))}
      </div>

      <SectionHeader>Comparison</SectionHeader>
      <label className="block space-y-1.5">
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
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1.5">
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
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Our features (one per line)</FieldLabel>
        <textarea
          disabled={disabled}
          rows={4}
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
          className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Competitor features (one per line)</FieldLabel>
        <textarea
          disabled={disabled}
          rows={4}
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
          className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
        />
      </label>

      <SectionHeader>Proof</SectionHeader>
      <label className="block space-y-1.5">
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
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Proof points (one per line)</FieldLabel>
        <textarea
          disabled={disabled}
          rows={4}
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
          className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
        />
      </label>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <SectionHeader>Objections</SectionHeader>
          <button
            type="button"
            disabled={disabled}
            onClick={addObjection}
            className="icon-btn shrink-0"
            aria-label="Add objection"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <label className="block space-y-1.5">
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
            className="fv-input px-3 py-2 text-sm"
          />
        </label>
        {objections.items.map((item, index) => (
          <div
            key={index}
            className="space-y-2 rounded-xl border border-[var(--fv-border)] p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <FieldLabel>Objection {index + 1}</FieldLabel>
              <button
                type="button"
                disabled={disabled}
                onClick={() => removeObjection(index)}
                className="icon-btn shrink-0"
                aria-label="Remove objection"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
            <input
              type="text"
              disabled={disabled}
              value={item.question}
              onChange={(e) =>
                updateObjection(index, "question", e.target.value)
              }
              placeholder="Question"
              className="fv-input px-3 py-2 text-sm"
            />
            <textarea
              disabled={disabled}
              rows={2}
              value={item.answer}
              onChange={(e) => updateObjection(index, "answer", e.target.value)}
              placeholder="Answer"
              className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
            />
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <SectionHeader>FAQ</SectionHeader>
          <button
            type="button"
            disabled={disabled}
            onClick={addFaq}
            className="icon-btn shrink-0"
            aria-label="Add FAQ"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        {faq.map((item, index) => (
          <div
            key={index}
            className="space-y-2 rounded-xl border border-[var(--fv-border)] p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <FieldLabel>Question {index + 1}</FieldLabel>
              <button
                type="button"
                disabled={disabled}
                onClick={() => removeFaq(index)}
                className="icon-btn shrink-0"
                aria-label="Remove FAQ"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
            <input
              type="text"
              disabled={disabled}
              value={item.question}
              onChange={(e) => updateFaq(index, "question", e.target.value)}
              placeholder="Question"
              className="fv-input px-3 py-2 text-sm"
            />
            <textarea
              disabled={disabled}
              rows={2}
              value={item.answer}
              onChange={(e) => updateFaq(index, "answer", e.target.value)}
              placeholder="Answer"
              className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
            />
          </div>
        ))}
      </div>

      <SectionHeader>CTA</SectionHeader>
      <label className="block space-y-1.5">
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
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1.5">
        <FieldLabel>Subheading</FieldLabel>
        <textarea
          disabled={disabled}
          rows={2}
          value={cta.subheading}
          onChange={(e) =>
            onChange({
              ...copy,
              cta: { ...cta, subheading: e.target.value },
            })
          }
          className="fv-input resize-none px-3 py-2 text-sm leading-relaxed"
        />
      </label>
      <label className="block space-y-1.5">
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
          className="fv-input px-3 py-2 text-sm"
        />
      </label>
    </div>
  );
}
