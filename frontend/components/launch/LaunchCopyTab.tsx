"use client";

// JSON key is 'cta', display label is 'Button text' — do not conflate
// (hero.cta → labeled "Button text"; final cta.button → labeled "Button").

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  getExperiment,
  getLandingPage,
  patchLandingPage,
} from "@/lib/api";
import { buildSyncedCopyPatch } from "@/lib/landing-copy-sync";
import {
  regenerateLandingSection,
  type RegeneratableSectionId,
} from "@/lib/landing-regen";
import { resolveLandingPageEditorData } from "@/lib/landing-page-data";
import { canEditLandingPage } from "@/lib/landing-flow";
import { useToast } from "@/components/ui/ToastProvider";
import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";
import type { CopyJson, FaqItem, FeatureCopy, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";

/** Client-side hard caps for Launch Copy tab (block save on overflow). */
const CAPS = {
  heroHeadline: 120,
  heroSubheadline: 300,
  heroCta: 40,
  problemHeading: 120,
  problemBody: 800,
  featureTitle: 80,
  featureDescription: 200,
  comparisonMetric: 120,
  comparisonCompetitor: 120,
  comparisonItem: 160,
  proofHeadline: 120,
  proofElement: 160,
  objectionsHeading: 120,
  faqQuestion: 200,
  faqAnswer: 400,
  ctaHeading: 120,
  ctaSubheading: 200,
  ctaButton: 40,
} as const;

const SECTION_META: {
  id: RegeneratableSectionId;
  label: string;
  hint: string;
}[] = [
  {
    id: "hero",
    label: "Hero",
    hint: "First screen — headline, subheadline, and button.",
  },
  {
    id: "problem",
    label: "Problem",
    hint: "The pain your audience feels today.",
  },
  {
    id: "features",
    label: "Features",
    hint: "Benefits and outcomes your product delivers.",
  },
  {
    id: "comparison",
    label: "Compare",
    hint: "How you stack up against alternatives.",
  },
  {
    id: "proof",
    label: "Proof",
    hint: "Signals that build trust and credibility.",
  },
  {
    id: "objections",
    label: "Objections",
    hint: "Questions and doubts, answered directly.",
  },
  {
    id: "faq",
    label: "FAQ",
    hint: "Common questions from potential customers.",
  },
  {
    id: "cta",
    label: "CTA",
    hint: "Final push to join the waitlist or sign up.",
  },
];

const MIN_FEATURES = 3;
const MAX_FEATURES = 5;
const MIN_FAQ = 3;
const MAX_FAQ = 5;

type LoadState =
  | { kind: "loading" }
  | { kind: "need_page" }
  | { kind: "generating" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

type Props = {
  experimentId: string;
  /** True while LaunchStagePanel is waiting on first/regen generate. */
  landingGenerating?: boolean;
  onGenerateLandingPage: () => void;
  /** Fired after a successful landing-page PATCH (autosave or regen). */
  onLandingPageSaved?: () => void;
};

function sectionPresent(copy: CopyJson, id: RegeneratableSectionId): boolean {
  const value = copy[id];
  if (value == null) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="mb-1 block font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/60">
      {children}
    </span>
  );
}

function BrutalistInput({
  value,
  onChange,
  maxLength,
  disabled,
  saving,
  placeholder,
  multiline,
  rows = 3,
}: {
  value: string;
  onChange: (next: string) => void;
  maxLength: number;
  disabled?: boolean;
  saving?: boolean;
  placeholder?: string;
  multiline?: boolean;
  rows?: number;
}) {
  const over = value.length > maxLength;
  const shared =
    "w-full border-2 border-border-master bg-surface-elevated px-3 py-2 font-body text-body-sm text-ink-primary outline-none focus:border-brand-primary disabled:opacity-50";

  return (
    <div>
      {multiline ? (
        <textarea
          value={value}
          disabled={disabled}
          rows={rows}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={`${shared} resize-y`}
        />
      ) : (
        <input
          type="text"
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={shared}
        />
      )}
      <div className="mt-1 flex items-center justify-between">
        <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
          {saving ? "saving…" : "\u00a0"}
        </span>
        <span
          className={`font-mono text-mono-sm ${
            over ? "text-status-critical" : "text-ink-tertiary"
          }`}
        >
          {value.length} / {maxLength}
        </span>
      </div>
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-label="Regenerating">
      <BrutalistSkeleton variant="block" height="h-10" />
      <BrutalistSkeleton variant="block" height="h-24" />
      <BrutalistSkeleton variant="block" height="h-10" />
    </div>
  );
}

export function LaunchCopyTab({
  experimentId,
  landingGenerating = false,
  onGenerateLandingPage,
  onLandingPageSaved,
}: Props) {
  const { toast } = useToast();
  const [loadState, setLoadState] = useState<LoadState>({ kind: "loading" });
  const [copy, setCopy] = useState<CopyJson>({});
  const [page, setPage] = useState<PageJson>({});
  const [templateId, setTemplateId] = useState<TemplateId>("dark-premium");
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);
  const [activeSection, setActiveSection] =
    useState<RegeneratableSectionId>("hero");
  const [saving, setSaving] = useState(false);
  const [regeneratingSection, setRegeneratingSection] =
    useState<RegeneratableSectionId | null>(null);

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveAbortRef = useRef<AbortController | null>(null);
  const copyRef = useRef(copy);
  const pageRef = useRef(page);
  const templateIdRef = useRef(templateId);

  copyRef.current = copy;
  pageRef.current = page;
  templateIdRef.current = templateId;

  const editable =
    loadState.kind === "ready" &&
    experimentStatus != null &&
    canEditLandingPage(experimentStatus) &&
    !landingGenerating &&
    regeneratingSection === null;

  const availableSections = SECTION_META.filter((s) =>
    sectionPresent(copy, s.id),
  );
  const availableSectionKey = availableSections.map((s) => s.id).join(",");

  useEffect(() => {
    if (availableSections.length === 0) return;
    if (!availableSections.some((s) => s.id === activeSection)) {
      setActiveSection(availableSections[0].id);
    }
    // availableSectionKey tracks membership without depending on a new array each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed by availableSectionKey
  }, [availableSectionKey, activeSection]);

  const loadLanding = useCallback(async () => {
    setLoadState({ kind: "loading" });
    try {
      const experiment = await getExperiment(experimentId);
      setExperimentStatus(experiment.status);

      if (experiment.status === "LANDING_GENERATING" || landingGenerating) {
        setLoadState({ kind: "generating" });
        return;
      }

      let lp;
      try {
        lp = await getLandingPage(experimentId);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setLoadState({ kind: "need_page" });
          return;
        }
        throw err;
      }

      const resolved = resolveLandingPageEditorData(lp);
      const nextCopy = resolved.copy;
      if (Object.keys(nextCopy).length === 0) {
        setLoadState({ kind: "need_page" });
        return;
      }

      setCopy(nextCopy);
      setPage(resolved.page);
      setTemplateId(resolved.templateId);
      setLoadState({ kind: "ready" });
    } catch {
      setLoadState({
        kind: "error",
        message: "Couldn't load copy — try again",
      });
    }
  }, [experimentId, landingGenerating]);

  useEffect(() => {
    void loadLanding();
  }, [loadLanding]);

  useEffect(() => {
    if (landingGenerating) {
      setLoadState({ kind: "generating" });
    }
  }, [landingGenerating]);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveAbortRef.current?.abort();
    };
  }, []);

  const persistCopy = useCallback(
    (nextCopy: CopyJson, nextPage: PageJson) => {
      const status = experimentStatus;
      if (
        status == null ||
        !canEditLandingPage(status) ||
        landingGenerating
      ) {
        return;
      }

      const patch = buildSyncedCopyPatch(
        nextCopy,
        nextPage,
        templateIdRef.current,
      );

      // Block if any string field exceeds caps (shallow walk of known shapes).
      if (copyExceedsCaps(patch.copy_json)) {
        return;
      }

      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      const snapshot = {
        copy: copyRef.current,
        page: pageRef.current,
      };
      setSaving(true);
      saveTimerRef.current = setTimeout(() => {
        saveAbortRef.current?.abort();
        const controller = new AbortController();
        saveAbortRef.current = controller;
        void patchLandingPage(
          experimentId,
          {
            copy_json: patch.copy_json,
            page_json: patch.page_json,
          },
          { signal: controller.signal },
        )
          .then(() => {
            if (!controller.signal.aborted) {
              setPage(patch.page_json);
              setSaving(false);
              onLandingPageSaved?.();
            }
          })
          .catch(() => {
            if (controller.signal.aborted) return;
            setCopy(snapshot.copy);
            setPage(snapshot.page);
            setSaving(false);
            toast("Couldn't save — try again", "error");
          });
      }, 500);
    },
    [
      experimentId,
      experimentStatus,
      landingGenerating,
      onLandingPageSaved,
      toast,
    ],
  );

  const applyCopy = useCallback(
    (nextCopy: CopyJson) => {
      setCopy(nextCopy);
      const synced = buildSyncedCopyPatch(
        nextCopy,
        pageRef.current,
        templateIdRef.current,
      ).page_json;
      setPage(synced);
      persistCopy(nextCopy, synced);
    },
    [persistCopy],
  );

  const handleRegenerate = async () => {
    if (!editable || regeneratingSection) return;
    const section = activeSection;
    setRegeneratingSection(section);
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    saveAbortRef.current?.abort();

    try {
      const result = await regenerateLandingSection({
        experimentId,
        templateId,
        section,
        copy: copyRef.current,
        page: pageRef.current,
      });

      if (result.unchangedAfterRetry) {
        toast(
          "Regeneration didn't produce a change — try adding a hint",
          "error",
        );
        return;
      }

      setCopy(result.copy);
      setPage(result.page);
      await patchLandingPage(experimentId, {
        copy_json: result.copy,
        page_json: result.page,
      });
      onLandingPageSaved?.();
      toast(
        `${section.charAt(0).toUpperCase()}${section.slice(1)} regenerated`,
        "success",
      );
    } catch {
      toast(
        "Regeneration didn't produce a change — try adding a hint",
        "error",
      );
    } finally {
      setRegeneratingSection(null);
      // Refresh status after async generate cycle.
      try {
        const experiment = await getExperiment(experimentId);
        setExperimentStatus(experiment.status);
      } catch {
        /* ignore */
      }
    }
  };

  if (loadState.kind === "loading") {
    return (
      <CopyShell>
        <p className="text-center font-mono text-mono-sm uppercase text-ink-primary/60">
          Loading copy…
        </p>
      </CopyShell>
    );
  }

  if (loadState.kind === "generating") {
    return (
      <CopyShell>
        <p className="text-center font-mono text-mono-sm uppercase text-ink-primary/60">
          Building your page — copy unlocks when it&apos;s ready.
        </p>
      </CopyShell>
    );
  }

  if (loadState.kind === "need_page") {
    return (
      <CopyShell>
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="max-w-xs font-mono text-mono-sm uppercase text-ink-primary/60">
            Your kit unlocks after your landing page is ready.
          </p>
          <button
            type="button"
            onClick={onGenerateLandingPage}
            className="border-2 border-border-master bg-brand-primary px-4 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-sm transition-all hover:shadow-brutal-md"
          >
            Generate landing page
          </button>
        </div>
      </CopyShell>
    );
  }

  if (loadState.kind === "error") {
    return (
      <CopyShell>
        <div className="flex flex-col items-center gap-3 text-center">
          <p className="font-mono text-mono-sm uppercase text-status-critical">
            {loadState.message}
          </p>
          <button
            type="button"
            onClick={() => void loadLanding()}
            className="border-2 border-border-master bg-surface-card px-3 py-2 font-label-md text-label-sm uppercase shadow-brutal-sm"
          >
            Retry
          </button>
        </div>
      </CopyShell>
    );
  }

  const meta =
    SECTION_META.find((s) => s.id === activeSection) ?? SECTION_META[0];
  const isRegen = regeneratingSection === activeSection;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className="flex shrink-0 gap-1 overflow-x-auto border-b-2 border-border-master bg-surface-card p-2"
        role="tablist"
        aria-label="Copy sections"
      >
        {availableSections.map((section) => {
          const active = activeSection === section.id;
          return (
            <button
              key={section.id}
              type="button"
              role="tab"
              aria-selected={active}
              disabled={!editable && regeneratingSection === null}
              onClick={() => setActiveSection(section.id)}
              className={`shrink-0 border-2 border-border-master px-2.5 py-1.5 font-label-sm text-label-sm uppercase tracking-wider transition-all ${
                active
                  ? "bg-brutalist-yellow text-ink-primary shadow-brutal-sm"
                  : "bg-surface-elevated text-ink-primary hover:-translate-y-0.5 hover:shadow-brutal-sm"
              }`}
            >
              {section.label}
            </button>
          );
        })}
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              {meta.label}
            </h3>
            <p className="mt-1 font-mono text-mono-sm uppercase text-ink-primary/60">
              {meta.hint}
            </p>
          </div>
          <button
            type="button"
            disabled={!editable || regeneratingSection !== null}
            onClick={() => void handleRegenerate()}
            className="inline-flex shrink-0 items-center gap-1.5 border-2 border-border-master bg-surface-card px-2.5 py-1.5 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span
              className={`material-symbols-outlined ${isRegen ? "animate-spin" : ""}`}
              style={{ fontSize: 16 }}
              aria-hidden="true"
            >
              refresh
            </span>
            {isRegen ? "…" : "Regenerate"}
          </button>
        </div>

        {isRegen ? (
          <SectionSkeleton />
        ) : (
          <SectionBody
            section={activeSection}
            copy={copy}
            disabled={!editable}
            saving={saving}
            onChange={applyCopy}
          />
        )}
      </div>
    </div>
  );
}

function CopyShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-1 items-center justify-center p-6">
      {children}
    </div>
  );
}

function copyExceedsCaps(copy: CopyJson): boolean {
  const hero = copy.hero;
  if (hero) {
    if ((hero.headline ?? "").length > CAPS.heroHeadline) return true;
    if ((hero.subheadline ?? "").length > CAPS.heroSubheadline) return true;
    if ((hero.cta ?? "").length > CAPS.heroCta) return true;
  }
  const problem = copy.problem;
  if (problem) {
    if ((problem.heading ?? "").length > CAPS.problemHeading) return true;
    if ((problem.body ?? "").length > CAPS.problemBody) return true;
  }
  for (const f of copy.features ?? []) {
    if ((f.title ?? "").length > CAPS.featureTitle) return true;
    if ((f.description ?? "").length > CAPS.featureDescription) return true;
  }
  const comparison = copy.comparison;
  if (comparison) {
    if ((comparison.metric_label ?? "").length > CAPS.comparisonMetric)
      return true;
    if ((comparison.competitor_name ?? "").length > CAPS.comparisonCompetitor)
      return true;
    for (const s of comparison.our_features ?? []) {
      if (s.length > CAPS.comparisonItem) return true;
    }
    for (const s of comparison.competitor_features ?? []) {
      if (s.length > CAPS.comparisonItem) return true;
    }
  }
  const proof = copy.proof;
  if (proof) {
    if ((proof.headline ?? "").length > CAPS.proofHeadline) return true;
    for (const e of proof.elements ?? []) {
      if (e.length > CAPS.proofElement) return true;
    }
  }
  const objections = copy.objections as
    | { heading?: string; items?: FaqItem[] }
    | undefined;
  if (objections) {
    if ((objections.heading ?? "").length > CAPS.objectionsHeading) return true;
    for (const item of objections.items ?? []) {
      if ((item.question ?? "").length > CAPS.faqQuestion) return true;
      if ((item.answer ?? "").length > CAPS.faqAnswer) return true;
    }
  }
  for (const item of copy.faq ?? []) {
    if ((item.question ?? "").length > CAPS.faqQuestion) return true;
    if ((item.answer ?? "").length > CAPS.faqAnswer) return true;
  }
  const cta = copy.cta;
  if (cta) {
    if ((cta.heading ?? "").length > CAPS.ctaHeading) return true;
    if ((cta.subheading ?? "").length > CAPS.ctaSubheading) return true;
    if ((cta.button ?? "").length > CAPS.ctaButton) return true;
  }
  return false;
}

function SectionBody({
  section,
  copy,
  disabled,
  saving,
  onChange,
}: {
  section: RegeneratableSectionId;
  copy: CopyJson;
  disabled: boolean;
  saving: boolean;
  onChange: (next: CopyJson) => void;
}) {
  const hero = copy.hero ?? { headline: "", subheadline: "", cta: "" };
  const problem = copy.problem ?? { heading: "", body: "" };
  const features = copy.features ?? [];
  const comparison = copy.comparison ?? {
    metric_label: "",
    competitor_name: "",
    our_features: [] as string[],
    competitor_features: [] as string[],
  };
  const proof = copy.proof ?? { headline: "", elements: [] as string[] };
  const objections = (copy.objections ?? {
    heading: "",
    items: [] as FaqItem[],
  }) as { heading: string; items: FaqItem[] };
  const faq = copy.faq ?? [];
  const cta = copy.cta ?? { heading: "", subheading: "", button: "" };

  if (section === "hero") {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <FieldLabel>Headline</FieldLabel>
          <BrutalistInput
            value={hero.headline}
            maxLength={CAPS.heroHeadline}
            disabled={disabled}
            saving={saving}
            onChange={(headline) =>
              onChange({ ...copy, hero: { ...hero, headline } })
            }
          />
        </div>
        <div>
          <FieldLabel>Subheadline</FieldLabel>
          <BrutalistInput
            multiline
            rows={3}
            value={hero.subheadline}
            maxLength={CAPS.heroSubheadline}
            disabled={disabled}
            saving={saving}
            onChange={(subheadline) =>
              onChange({ ...copy, hero: { ...hero, subheadline } })
            }
          />
        </div>
        <div>
          <FieldLabel>Button text</FieldLabel>
          <BrutalistInput
            value={hero.cta}
            maxLength={CAPS.heroCta}
            disabled={disabled}
            saving={saving}
            onChange={(ctaValue) =>
              onChange({ ...copy, hero: { ...hero, cta: ctaValue } })
            }
          />
        </div>
      </div>
    );
  }

  if (section === "problem") {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <FieldLabel>Heading</FieldLabel>
          <BrutalistInput
            value={problem.heading}
            maxLength={CAPS.problemHeading}
            disabled={disabled}
            saving={saving}
            onChange={(heading) =>
              onChange({ ...copy, problem: { ...problem, heading } })
            }
          />
        </div>
        <div>
          <FieldLabel>Body</FieldLabel>
          <BrutalistInput
            multiline
            rows={5}
            value={problem.body}
            maxLength={CAPS.problemBody}
            disabled={disabled}
            saving={saving}
            onChange={(body) =>
              onChange({ ...copy, problem: { ...problem, body } })
            }
          />
        </div>
      </div>
    );
  }

  if (section === "features") {
    return (
      <div className="flex flex-col gap-4">
        {features.map((feature, index) => (
          <div
            key={index}
            className="border-2 border-border-master bg-surface-card p-3 shadow-brutal-sm"
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="font-label-sm text-label-sm uppercase text-ink-primary/60">
                Feature {index + 1}
              </span>
              <button
                type="button"
                disabled={disabled || features.length <= MIN_FEATURES}
                onClick={() =>
                  onChange({
                    ...copy,
                    features: features.filter((_, i) => i !== index),
                  })
                }
                className="font-mono text-mono-sm uppercase text-ink-tertiary hover:text-status-critical disabled:opacity-40"
              >
                Remove
              </button>
            </div>
            <div className="flex flex-col gap-3">
              <div>
                <FieldLabel>Title</FieldLabel>
                <BrutalistInput
                  value={feature.title}
                  maxLength={CAPS.featureTitle}
                  disabled={disabled}
                  saving={saving}
                  onChange={(title) => {
                    const next = features.map((f, i) =>
                      i === index ? { ...f, title } : f,
                    );
                    onChange({ ...copy, features: next });
                  }}
                />
              </div>
              <div>
                <FieldLabel>Description</FieldLabel>
                <BrutalistInput
                  multiline
                  value={feature.description}
                  maxLength={CAPS.featureDescription}
                  disabled={disabled}
                  saving={saving}
                  onChange={(description) => {
                    const next = features.map((f, i) =>
                      i === index ? { ...f, description } : f,
                    );
                    onChange({ ...copy, features: next });
                  }}
                />
              </div>
            </div>
          </div>
        ))}
        <button
          type="button"
          disabled={disabled || features.length >= MAX_FEATURES}
          onClick={() =>
            onChange({
              ...copy,
              features: [
                ...features,
                { title: "", description: "" } satisfies FeatureCopy,
              ],
            })
          }
          className="border-2 border-dashed border-border-master px-3 py-2 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/70 disabled:opacity-40"
        >
          Add feature
        </button>
      </div>
    );
  }

  if (section === "comparison") {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <FieldLabel>Metric label</FieldLabel>
          <BrutalistInput
            value={comparison.metric_label}
            maxLength={CAPS.comparisonMetric}
            disabled={disabled}
            saving={saving}
            onChange={(metric_label) =>
              onChange({
                ...copy,
                comparison: { ...comparison, metric_label },
              })
            }
          />
        </div>
        <div>
          <FieldLabel>Competitor name</FieldLabel>
          <BrutalistInput
            value={comparison.competitor_name}
            maxLength={CAPS.comparisonCompetitor}
            disabled={disabled}
            saving={saving}
            onChange={(competitor_name) =>
              onChange({
                ...copy,
                comparison: { ...comparison, competitor_name },
              })
            }
          />
        </div>
        <StringListEditor
          label="Our features"
          items={comparison.our_features ?? []}
          maxLength={CAPS.comparisonItem}
          disabled={disabled}
          saving={saving}
          onChange={(our_features) =>
            onChange({
              ...copy,
              comparison: { ...comparison, our_features },
            })
          }
        />
        <StringListEditor
          label="Competitor features"
          items={comparison.competitor_features ?? []}
          maxLength={CAPS.comparisonItem}
          disabled={disabled}
          saving={saving}
          onChange={(competitor_features) =>
            onChange({
              ...copy,
              comparison: { ...comparison, competitor_features },
            })
          }
        />
      </div>
    );
  }

  if (section === "proof") {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <FieldLabel>Headline</FieldLabel>
          <BrutalistInput
            value={proof.headline}
            maxLength={CAPS.proofHeadline}
            disabled={disabled}
            saving={saving}
            onChange={(headline) =>
              onChange({ ...copy, proof: { ...proof, headline } })
            }
          />
        </div>
        <StringListEditor
          label="Elements"
          items={proof.elements ?? []}
          maxLength={CAPS.proofElement}
          disabled={disabled}
          saving={saving}
          onChange={(elements) =>
            onChange({ ...copy, proof: { ...proof, elements } })
          }
        />
      </div>
    );
  }

  if (section === "objections") {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <FieldLabel>Heading</FieldLabel>
          <BrutalistInput
            value={objections.heading}
            maxLength={CAPS.objectionsHeading}
            disabled={disabled}
            saving={saving}
            onChange={(heading) =>
              onChange({
                ...copy,
                objections: { ...objections, heading },
              })
            }
          />
        </div>
        <QaListEditor
          items={objections.items}
          disabled={disabled}
          saving={saving}
          onChange={(items) =>
            onChange({
              ...copy,
              objections: { ...objections, items },
            })
          }
        />
      </div>
    );
  }

  if (section === "faq") {
    return (
      <div className="flex flex-col gap-4">
        <QaListEditor
          items={faq}
          disabled={disabled}
          saving={saving}
          minItems={MIN_FAQ}
          maxItems={MAX_FAQ}
          onChange={(items) => onChange({ ...copy, faq: items })}
        />
      </div>
    );
  }

  // cta
  return (
    <div className="flex flex-col gap-4">
      <div>
        <FieldLabel>Heading</FieldLabel>
        <BrutalistInput
          value={cta.heading}
          maxLength={CAPS.ctaHeading}
          disabled={disabled}
          saving={saving}
          onChange={(heading) =>
            onChange({ ...copy, cta: { ...cta, heading } })
          }
        />
      </div>
      <div>
        <FieldLabel>Subheading</FieldLabel>
        <BrutalistInput
          value={cta.subheading}
          maxLength={CAPS.ctaSubheading}
          disabled={disabled}
          saving={saving}
          onChange={(subheading) =>
            onChange({ ...copy, cta: { ...cta, subheading } })
          }
        />
      </div>
      <div>
        <FieldLabel>Button</FieldLabel>
        <BrutalistInput
          value={cta.button}
          maxLength={CAPS.ctaButton}
          disabled={disabled}
          saving={saving}
          onChange={(button) =>
            onChange({ ...copy, cta: { ...cta, button } })
          }
        />
      </div>
    </div>
  );
}

function StringListEditor({
  label,
  items,
  maxLength,
  disabled,
  saving,
  onChange,
}: {
  label: string;
  items: string[];
  maxLength: number;
  disabled: boolean;
  saving: boolean;
  onChange: (next: string[]) => void;
}) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="flex flex-col gap-2">
        {items.map((item, index) => (
          <div key={index} className="flex flex-col gap-1">
            <BrutalistInput
              value={item}
              maxLength={maxLength}
              disabled={disabled}
              saving={saving}
              onChange={(value) => {
                const next = items.map((s, i) => (i === index ? value : s));
                onChange(next);
              }}
            />
            <button
              type="button"
              disabled={disabled || items.length <= 1}
              onClick={() => onChange(items.filter((_, i) => i !== index))}
              className="self-end font-mono text-mono-sm uppercase text-ink-tertiary hover:text-status-critical disabled:opacity-40"
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange([...items, ""])}
          className="border-2 border-dashed border-border-master px-3 py-2 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/70 disabled:opacity-40"
        >
          Add item
        </button>
      </div>
    </div>
  );
}

function QaListEditor({
  items,
  disabled,
  saving,
  onChange,
  minItems = 0,
  maxItems = 20,
}: {
  items: FaqItem[];
  disabled: boolean;
  saving: boolean;
  onChange: (next: FaqItem[]) => void;
  minItems?: number;
  maxItems?: number;
}) {
  return (
    <div className="flex flex-col gap-4">
      {items.map((item, index) => (
        <div
          key={index}
          className="border-2 border-border-master bg-surface-card p-3 shadow-brutal-sm"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="font-label-sm text-label-sm uppercase text-ink-primary/60">
              Item {index + 1}
            </span>
            <button
              type="button"
              disabled={disabled || items.length <= minItems}
              onClick={() => onChange(items.filter((_, i) => i !== index))}
              className="font-mono text-mono-sm uppercase text-ink-tertiary hover:text-status-critical disabled:opacity-40"
            >
              Remove
            </button>
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <FieldLabel>Question</FieldLabel>
              <BrutalistInput
                value={item.question}
                maxLength={CAPS.faqQuestion}
                disabled={disabled}
                saving={saving}
                onChange={(question) => {
                  const next = items.map((row, i) =>
                    i === index ? { ...row, question } : row,
                  );
                  onChange(next);
                }}
              />
            </div>
            <div>
              <FieldLabel>Answer</FieldLabel>
              <BrutalistInput
                multiline
                value={item.answer}
                maxLength={CAPS.faqAnswer}
                disabled={disabled}
                saving={saving}
                onChange={(answer) => {
                  const next = items.map((row, i) =>
                    i === index ? { ...row, answer } : row,
                  );
                  onChange(next);
                }}
              />
            </div>
          </div>
        </div>
      ))}
      <button
        type="button"
        disabled={disabled || items.length >= maxItems}
        onClick={() =>
          onChange([...items, { question: "", answer: "" }])
        }
        className="border-2 border-dashed border-border-master px-3 py-2 font-label-sm text-label-sm uppercase tracking-wider text-ink-primary/70 disabled:opacity-40"
      >
        Add item
      </button>
    </div>
  );
}
