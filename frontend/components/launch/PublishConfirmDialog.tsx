"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  ApiError,
  getLandingPage,
  publishProject,
} from "@/lib/api";
import type { LandingPage } from "@/lib/types";
import { LandingPageSlugEditor } from "@/components/landing-page-editor/LandingPageSlugEditor";

type Props = {
  open: boolean;
  experimentId: string;
  projectName: string;
  onClose: () => void;
  onPublished: (result: { slug: string; public_url: string }) => void;
};

function previewLines(page: LandingPage): {
  headline: string;
  subhead: string;
  cta: string;
} {
  const hero = page.copy_json?.hero;
  const headline = (hero?.headline ?? page.headline ?? "Untitled").trim();
  const rawSub = (hero?.subheadline ?? page.subheadline ?? "").trim();
  const subhead =
    rawSub.length <= 30 ? rawSub : `${rawSub.slice(0, 30).trimEnd()}…`;
  const cta = (hero?.cta ?? page.copy_json?.cta?.button ?? "Join waitlist").trim();
  return { headline, subhead, cta };
}

/**
 * Confirm publish: slug editor + 3-line preview. Always sends cta_mode: "waitlist"
 * (backend currently ignores the body; picker deferred until cta_mode is real).
 */
export function PublishConfirmDialog({
  open,
  experimentId,
  projectName,
  onClose,
  onPublished,
}: Props) {
  const [page, setPage] = useState<LandingPage | null>(null);
  const [slug, setSlug] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPublishing(false);
    (async () => {
      try {
        const lp = await getLandingPage(experimentId);
        if (cancelled) return;
        setPage(lp);
        setSlug(lp.slug);
        setLoading(false);
      } catch {
        if (cancelled) return;
        setError("Could not load landing page.");
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, experimentId]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !publishing) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, publishing, onClose]);

  async function handlePublish() {
    if (!slug) {
      setError("Set a URL slug before publishing.");
      return;
    }
    setPublishing(true);
    setError(null);
    try {
      const res = await publishProject(experimentId, {
        slug,
        cta_mode: "waitlist",
      });
      onPublished({ slug: res.slug, public_url: res.public_url });
    } catch (err) {
      const detail =
        err instanceof ApiError &&
        typeof err.body === "object" &&
        err.body !== null &&
        "detail" in err.body &&
        typeof (err.body as { detail: unknown }).detail === "string"
          ? (err.body as { detail: string }).detail
          : "Publish failed — try again.";
      setError(detail);
      setPublishing(false);
    }
  }

  if (!open || typeof document === "undefined") return null;

  const preview = page ? previewLines(page) : null;

  return createPortal(
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-ink-primary/50 p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="publish-confirm-title"
    >
      <div className="w-full max-w-lg border-2 border-border-master bg-surface-card shadow-brutal-md">
        <div className="border-b-2 border-border-master p-6">
          <h2
            id="publish-confirm-title"
            className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary"
          >
            Publish landing page
          </h2>
          <p className="mt-1 font-mono text-mono-sm uppercase text-ink-primary/60">
            Make it live at your public URL
          </p>
        </div>

        <div className="space-y-6 p-6">
          {error ? (
            <div
              className="border-2 border-status-critical bg-status-critical/10 p-3 font-mono text-mono-sm uppercase text-status-critical"
              role="alert"
            >
              {error}
            </div>
          ) : null}

          {loading ? (
            <p className="font-mono text-mono-sm uppercase text-ink-primary/60">
              Loading…
            </p>
          ) : page ? (
            <>
              {/* Slug — LandingPageSlugEditor is fv-*; chrome is brutalist wrapper only */}
              <div>
                <span className="mb-2 block font-label-md text-label-md uppercase text-ink-primary">
                  Public URL
                </span>
                <div className="border-2 border-border-master bg-surface-card p-3 shadow-brutal-sm">
                  <LandingPageSlugEditor
                    experimentId={experimentId}
                    currentSlug={slug}
                    projectName={projectName}
                    embedded
                    onSlugSaved={setSlug}
                  />
                </div>
              </div>

              {preview ? (
                <div>
                  <span className="mb-2 block font-label-md text-label-md uppercase text-ink-primary">
                    Preview
                  </span>
                  <div className="border-2 border-border-master bg-surface-elevated p-4 shadow-brutal-sm">
                    <p className="font-headline text-headline-md text-ink-primary">
                      {preview.headline}
                    </p>
                    {preview.subhead ? (
                      <p className="mt-1 text-body-md text-ink-primary/70">
                        {preview.subhead}
                      </p>
                    ) : null}
                    <p className="mt-3 font-label-md text-label-sm uppercase text-brand-primary">
                      {preview.cta}
                    </p>
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </div>

        <div className="flex gap-3 border-t-2 border-border-master p-4">
          <button
            type="button"
            onClick={onClose}
            disabled={publishing}
            className="flex-1 border-2 border-border-master bg-surface-card px-4 py-3 font-label-md text-label-md uppercase text-ink-primary shadow-brutal-sm transition-all hover:shadow-brutal-md disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handlePublish()}
            disabled={publishing || loading || !page}
            className="flex-1 border-2 border-border-master bg-brand-primary px-4 py-3 font-label-md text-label-md uppercase text-ink-inverse shadow-brutal-md transition-all hover:shadow-brutal-lg disabled:opacity-50"
          >
            {publishing ? "Publishing…" : "Publish this page"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
