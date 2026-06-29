"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import type { CopyJson, FaqItem, FeatureCopy } from "@/lib/types";

interface CopyFieldsEditorProps {
  copy: CopyJson;
  onChange: (copy: CopyJson) => void;
  disabled?: boolean;
  onRegenerateSection?: (section: CopySectionId) => void;
  regeneratingSection?: CopySectionId | null;
}

export type CopySectionId =
  | "hero"
  | "problem"
  | "features"
  | "comparison"
  | "proof"
  | "objections"
  | "faq"
  | "cta";

const SECTIONS: {
  id: CopySectionId;
  label: string;
  hint: string;
}[] = [
  { id: "hero", label: "Hero", hint: "First screen — headline, subheadline, and button." },
  { id: "problem", label: "Problem", hint: "The pain your audience feels today." },
  { id: "features", label: "Features", hint: "Benefits and outcomes your product delivers." },
  { id: "comparison", label: "Compare", hint: "How you stack up against alternatives." },
  { id: "proof", label: "Proof", hint: "Signals that build trust and credibility." },
  { id: "objections", label: "Objections", hint: "Questions and doubts, answered directly." },
  { id: "faq", label: "FAQ", hint: "Common questions from potential customers." },
  { id: "cta", label: "CTA", hint: "Final push to join the waitlist or sign up." },
];

function CopyField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="lp-copy-field">
      <span className="lp-copy-field-label">{label}</span>
      {children}
    </div>
  );
}

function ListItem({
  title,
  onRemove,
  disabled,
  children,
}: {
  title: string;
  onRemove: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="lp-copy-list-item">
      <div className="lp-copy-list-item-head">
        <span className="lp-copy-list-item-title">{title}</span>
        <button
          type="button"
          disabled={disabled}
          onClick={onRemove}
          className="lp-copy-remove-btn"
          aria-label={`Remove ${title}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      {children}
    </div>
  );
}

export function CopyFieldsEditor({
  copy,
  onChange,
  disabled,
  onRegenerateSection,
  regeneratingSection,
}: CopyFieldsEditorProps) {
  const [activeSection, setActiveSection] = useState<CopySectionId>("hero");

  useEffect(() => {
    if (!regeneratingSection) return;
    setActiveSection(regeneratingSection);
  }, [regeneratingSection]);

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

  const inputClass = "lp-copy-input";
  const textareaClass = "lp-copy-input lp-copy-textarea";

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

  const sectionPanels: Record<CopySectionId, ReactNode> = {
    hero: (
      <>
        <CopyField label="Headline">
          <input
            type="text"
            disabled={disabled}
            value={hero.headline}
            onChange={(e) => updateHero("headline", e.target.value)}
            className={inputClass}
            placeholder="Your main hook"
          />
        </CopyField>
        <CopyField label="Subheadline">
          <textarea
            disabled={disabled}
            value={hero.subheadline}
            onChange={(e) => updateHero("subheadline", e.target.value)}
            className={textareaClass}
            placeholder="Who it's for and what they get"
          />
        </CopyField>
        <CopyField label="Button text">
          <input
            type="text"
            disabled={disabled}
            value={hero.cta}
            onChange={(e) => updateHero("cta", e.target.value)}
            className={inputClass}
            placeholder="Join the waitlist"
          />
        </CopyField>
      </>
    ),
    problem: (
      <>
        <CopyField label="Heading">
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
            className={inputClass}
            placeholder="The problem in one line"
          />
        </CopyField>
        <CopyField label="Body">
          <textarea
            disabled={disabled}
            value={problem.body}
            onChange={(e) =>
              onChange({
                ...copy,
                problem: { ...problem, body: e.target.value },
              })
            }
            className={textareaClass}
            placeholder="Expand on the pain and why it matters now"
          />
        </CopyField>
      </>
    ),
    features: (
      <div className="lp-copy-list">
        {features.map((feature, index) => (
          <ListItem
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
              placeholder="Benefit headline"
              className={inputClass}
            />
            <textarea
              disabled={disabled}
              value={feature.description}
              onChange={(e) =>
                updateFeature(index, "description", e.target.value)
              }
              placeholder="What the user gets"
              className={textareaClass}
            />
          </ListItem>
        ))}
        <button
          type="button"
          disabled={disabled}
          onClick={addFeature}
          className="lp-copy-add-btn"
        >
          <Plus className="h-3.5 w-3.5" />
          Add feature
        </button>
      </div>
    ),
    comparison: (
      <>
        <CopyField label="Metric label">
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
            className={inputClass}
            placeholder="What you measure"
          />
        </CopyField>
        <CopyField label="Competitor name">
          <input
            type="text"
            disabled={disabled}
            value={comparison.competitor_name}
            onChange={(e) =>
              onChange({
                ...copy,
                comparison: {
                  ...comparison,
                  competitor_name: e.target.value,
                },
              })
            }
            className={inputClass}
            placeholder="Alternative or incumbent"
          />
        </CopyField>
        <CopyField label="Our strengths">
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
            className={textareaClass}
            placeholder="One strength per line"
          />
        </CopyField>
        <CopyField label="Their weaknesses">
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
            className={textareaClass}
            placeholder="One gap per line"
          />
        </CopyField>
      </>
    ),
    proof: (
      <>
        <CopyField label="Headline">
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
            className={inputClass}
            placeholder="Why people trust this"
          />
        </CopyField>
        <CopyField label="Proof points">
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
            className={textareaClass}
            placeholder="One proof point per line"
          />
        </CopyField>
      </>
    ),
    objections: (
      <>
        <CopyField label="Section heading">
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
            className={inputClass}
            placeholder="You might be wondering…"
          />
        </CopyField>
        <div className="lp-copy-list">
          {objections.items.map((item, index) => (
            <ListItem
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
                placeholder="Concern or doubt"
                className={inputClass}
              />
              <textarea
                disabled={disabled}
                value={item.answer}
                onChange={(e) =>
                  updateObjection(index, "answer", e.target.value)
                }
                placeholder="Direct answer"
                className={textareaClass}
              />
            </ListItem>
          ))}
          <button
            type="button"
            disabled={disabled}
            onClick={addObjection}
            className="lp-copy-add-btn"
          >
            <Plus className="h-3.5 w-3.5" />
            Add objection
          </button>
        </div>
      </>
    ),
    faq: (
      <div className="lp-copy-list">
        {faq.map((item, index) => (
          <ListItem
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
              className={inputClass}
            />
            <textarea
              disabled={disabled}
              value={item.answer}
              onChange={(e) => updateFaq(index, "answer", e.target.value)}
              placeholder="Answer"
              className={textareaClass}
            />
          </ListItem>
        ))}
        <button
          type="button"
          disabled={disabled}
          onClick={addFaq}
          className="lp-copy-add-btn"
        >
          <Plus className="h-3.5 w-3.5" />
          Add question
        </button>
      </div>
    ),
    cta: (
      <>
        <CopyField label="Heading">
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
            className={inputClass}
            placeholder="Ready to get started?"
          />
        </CopyField>
        <CopyField label="Subheading">
          <textarea
            disabled={disabled}
            value={cta.subheading}
            onChange={(e) =>
              onChange({
                ...copy,
                cta: { ...cta, subheading: e.target.value },
              })
            }
            className={textareaClass}
            placeholder="Urgency or exclusivity"
          />
        </CopyField>
        <CopyField label="Button text">
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
            className={inputClass}
            placeholder="Join the waitlist"
          />
        </CopyField>
      </>
    ),
  };

  const activeMeta = SECTIONS.find((s) => s.id === activeSection) ?? SECTIONS[0];
  const isRegenerating = regeneratingSection === activeSection;

  return (
    <div className="lp-copy-editor">
      <div className="lp-copy-section-tabs" role="tablist" aria-label="Copy sections">
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            type="button"
            role="tab"
            aria-selected={activeSection === section.id}
            disabled={disabled}
            onClick={() => setActiveSection(section.id)}
            className={`lp-copy-section-tab${
              activeSection === section.id ? " lp-copy-section-tab-active" : ""
            }`}
          >
            {section.label}
          </button>
        ))}
      </div>

      <div className="lp-copy-panel" role="tabpanel">
        <div className="lp-copy-panel-header">
          <div>
            <div className="lp-copy-panel-title">{activeMeta.label}</div>
            <p className="lp-copy-panel-hint">{activeMeta.hint}</p>
          </div>
          {onRegenerateSection ? (
            <button
              type="button"
              disabled={disabled || regeneratingSection !== null}
              onClick={() => onRegenerateSection(activeSection)}
              className="lp-copy-regen-btn"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isRegenerating ? "animate-spin" : ""}`}
              />
              {isRegenerating ? "Regenerating…" : "Regenerate"}
            </button>
          ) : null}
        </div>
        <div className="lp-copy-fields">{sectionPanels[activeSection]}</div>
      </div>
    </div>
  );
}
