"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  getExperiment,
  getLandingPage,
  patchLandingPage,
} from "@/lib/api";
import { resolveLandingPageEditorData } from "@/lib/landing-page-data";
import { canEditLandingPage } from "@/lib/landing-flow";
import { useToast } from "@/components/ui/ToastProvider";
import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import { TemplatePanel } from "./TemplatePanel";
import { ColorThemePanel } from "./ColorThemePanel";
import { BrandIconPanel } from "./BrandIconPanel";
import { SurfaceAtmospherePanel } from "./SurfaceAtmospherePanel";

type LoadState =
  | { kind: "loading" }
  | { kind: "need_page" }
  | { kind: "generating" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

type Props = {
  experimentId: string;
  landingGenerating?: boolean;
  onGenerateLandingPage: () => void;
};

/**
 * Launch Design tab — four collapsible panels writing page_json only.
 * Template switch also sends template_id in the same PATCH.
 */
export function LaunchDesignTab({
  experimentId,
  landingGenerating = false,
  onGenerateLandingPage,
}: Props) {
  const { toast } = useToast();
  const [loadState, setLoadState] = useState<LoadState>({ kind: "loading" });
  const [copy, setCopy] = useState<CopyJson>({});
  const [page, setPage] = useState<PageJson>({});
  const [templateId, setTemplateId] = useState<TemplateId>("dark-premium");
  const [projectName, setProjectName] = useState("Untitled");
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveAbortRef = useRef<AbortController | null>(null);
  const pageRef = useRef(page);
  const templateIdRef = useRef(templateId);
  pageRef.current = page;
  templateIdRef.current = templateId;

  const editable =
    loadState.kind === "ready" &&
    experimentStatus != null &&
    canEditLandingPage(experimentStatus) &&
    !landingGenerating;

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

      const name =
        experiment.name?.trim() ||
        lp.headline?.trim() ||
        "Untitled project";
      const resolved = resolveLandingPageEditorData(lp, name);
      if (Object.keys(resolved.copy).length === 0) {
        setLoadState({ kind: "need_page" });
        return;
      }

      setCopy(resolved.copy);
      setPage(resolved.page);
      setTemplateId(resolved.templateId);
      setProjectName(resolved.projectName);
      setLoadState({ kind: "ready" });
    } catch {
      setLoadState({
        kind: "error",
        message: "Couldn't load design — try again",
      });
    }
  }, [experimentId, landingGenerating]);

  useEffect(() => {
    void loadLanding();
  }, [loadLanding]);

  useEffect(() => {
    if (landingGenerating) setLoadState({ kind: "generating" });
  }, [landingGenerating]);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveAbortRef.current?.abort();
    };
  }, []);

  const persistPage = useCallback(
    (
      nextPage: PageJson,
      options?: { templateId?: TemplateId },
    ) => {
      const status = experimentStatus;
      if (
        status == null ||
        !canEditLandingPage(status) ||
        landingGenerating
      ) {
        return;
      }

      const nextTemplateId = options?.templateId ?? templateIdRef.current;
      const snapshot = {
        page: pageRef.current,
        templateId: templateIdRef.current,
      };

      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      setSaving(true);
      saveTimerRef.current = setTimeout(() => {
        saveAbortRef.current?.abort();
        const controller = new AbortController();
        saveAbortRef.current = controller;
        const body: {
          page_json: PageJson;
          template_id?: string;
        } = {
          page_json: {
            ...nextPage,
            template_id: nextTemplateId,
          },
        };
        if (options?.templateId != null) {
          body.template_id = options.templateId;
        }

        void patchLandingPage(experimentId, body, {
          signal: controller.signal,
        })
          .then(() => {
            if (!controller.signal.aborted) {
              setSaving(false);
            }
          })
          .catch(() => {
            if (controller.signal.aborted) return;
            setPage(snapshot.page);
            setTemplateId(snapshot.templateId);
            setSaving(false);
            toast("Couldn't save — try again", "error");
          });
      }, 500);
    },
    [experimentId, experimentStatus, landingGenerating, toast],
  );

  const handlePageChange = useCallback(
    (nextPage: PageJson) => {
      setPage(nextPage);
      persistPage(nextPage);
    },
    [persistPage],
  );

  const handleTemplateSelect = useCallback(
    (id: TemplateId, nextPage: PageJson) => {
      setTemplateId(id);
      setPage(nextPage);
      persistPage(nextPage, { templateId: id });
    },
    [persistPage],
  );

  if (loadState.kind === "loading") {
    return (
      <Shell>
        <p className="text-center font-mono text-mono-sm uppercase text-ink-primary/60">
          Loading design…
        </p>
      </Shell>
    );
  }

  if (loadState.kind === "generating") {
    return (
      <Shell>
        <p className="text-center font-mono text-mono-sm uppercase text-ink-primary/60">
          Building your page — design unlocks when it&apos;s ready.
        </p>
      </Shell>
    );
  }

  if (loadState.kind === "need_page") {
    return (
      <Shell>
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
      </Shell>
    );
  }

  if (loadState.kind === "error") {
    return (
      <Shell>
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
      </Shell>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center justify-between border-b-2 border-border-master bg-surface-elevated px-3 py-2">
        <p className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
          Design
        </p>
        <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
          {saving ? "saving…" : "\u00a0"}
        </span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        <TemplatePanel
          templateId={templateId}
          copy={copy}
          page={page}
          disabled={!editable}
          onSelect={handleTemplateSelect}
        />
        <ColorThemePanel
          templateId={templateId}
          page={page}
          disabled={!editable}
          onChange={handlePageChange}
        />
        <BrandIconPanel
          experimentId={experimentId}
          templateId={templateId}
          projectName={projectName}
          page={page}
          disabled={!editable}
          onChange={handlePageChange}
        />
        <SurfaceAtmospherePanel
          page={page}
          disabled={!editable}
          onChange={handlePageChange}
        />
      </div>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-1 items-center justify-center p-6">
      {children}
    </div>
  );
}
