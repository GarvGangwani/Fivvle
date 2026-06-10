"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listPublications,
  publishProject,
  type PublicationSummary,
  type PublishProjectResponse,
} from "@/lib/api";
import { CTA_MODE_OPTIONS, type CtaMode } from "@/lib/cta-config";
import { slugifyProjectName } from "@/lib/published-page";

interface PublishPanelProps {
  projectId: string;
  projectName: string;
  outputVersion: number;
  disabled?: boolean;
  fullWidth?: boolean;
  onPublished?: (result: PublishProjectResponse) => void;
}

export function PublishPanel({
  projectId,
  projectName,
  outputVersion,
  disabled,
  fullWidth = false,
  onPublished,
}: PublishPanelProps) {
  const [slug, setSlug] = useState(() => slugifyProjectName(projectName));
  const [ctaMode, setCtaMode] = useState<CtaMode>("waitlist");
  const [ctaUrl, setCtaUrl] = useState("");
  const [isPublishing, setIsPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPublish, setLastPublish] = useState<PublishProjectResponse | null>(
    null,
  );
  const [history, setHistory] = useState<PublicationSummary[]>([]);

  const loadHistory = useCallback(async () => {
    try {
      const pubs = await listPublications(projectId);
      setHistory(pubs);
      const current = pubs.find((p) => p.is_current);
      if (current) {
        setSlug(current.slug);
      }
    } catch {
      /* optional */
    }
  }, [projectId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handlePublish = async () => {
    setIsPublishing(true);
    setError(null);
    try {
      const res = await publishProject(projectId, {
        slug: slug.trim() || undefined,
        cta_mode: ctaMode,
        cta_url: ctaMode === "external" ? ctaUrl.trim() : undefined,
      });
      setLastPublish(res);
      onPublished?.(res);
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed.");
    } finally {
      setIsPublishing(false);
    }
  };

  const copyLink = (url: string) => {
    void navigator.clipboard.writeText(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="fv-panel-label text-[var(--fv-accent)]">Publish to Fivvle</p>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
            Snapshot v{outputVersion} — live page uses the same templates as preview.
          </p>
        </div>
        {lastPublish && (
          <a
            href={lastPublish.public_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-[var(--fv-accent)]/30 bg-[var(--fv-accent-muted)] px-3 py-1.5 text-xs font-medium text-[var(--fv-accent)] hover:bg-[var(--fv-accent-muted)]"
          >
            Open live page ↗
          </a>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 sm:col-span-2">
          <span className="text-xs text-[var(--fv-text-muted)]">URL slug</span>
          <div className="flex items-center gap-0 overflow-hidden rounded-lg border border-[var(--fv-border)] bg-white/[0.04]">
            <span className="shrink-0 px-3 py-2 text-xs text-[var(--fv-text-muted)]">
              /p/
            </span>
            <input
              type="text"
              value={slug}
              disabled={disabled || isPublishing}
              onChange={(e) =>
                setSlug(
                  e.target.value
                    .toLowerCase()
                    .replace(/[^a-z0-9-]/g, "-")
                    .replace(/-+/g, "-"),
                )
              }
              className="flex-1 bg-transparent py-2 pr-3 font-mono text-sm text-[var(--fv-text)] outline-none"
            />
          </div>
        </label>

        <fieldset className="space-y-2 sm:col-span-2">
          <span className="text-xs text-[var(--fv-text-muted)]">CTA behavior</span>
          <div className="grid gap-2 sm:grid-cols-3">
            {CTA_MODE_OPTIONS.map((opt) => (
              <label
                key={opt.id}
                className={`cursor-pointer rounded-lg border p-3 text-left transition-colors ${
                  ctaMode === opt.id
                    ? "border-[var(--fv-accent)]/50 bg-[var(--fv-accent-muted)]"
                    : "border-[var(--fv-border)] hover:border-[var(--fv-border-strong)]"
                }`}
              >
                <input
                  type="radio"
                  name="cta_mode"
                  value={opt.id}
                  checked={ctaMode === opt.id}
                  disabled={disabled || isPublishing}
                  onChange={() => setCtaMode(opt.id)}
                  className="sr-only"
                />
                <p className="text-sm font-medium text-[var(--fv-text)]">{opt.label}</p>
                <p className="mt-1 text-xs text-[var(--fv-text-muted)]">{opt.description}</p>
              </label>
            ))}
          </div>
        </fieldset>

        {ctaMode === "external" && (
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs text-[var(--fv-text-muted)]">Destination URL</span>
            <input
              type="url"
              value={ctaUrl}
              disabled={disabled || isPublishing}
              onChange={(e) => setCtaUrl(e.target.value)}
              placeholder="https://calendly.com/your-link"
              className="fv-input px-3 py-2 text-sm"
            />
          </label>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}

      {lastPublish && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--fv-border)] bg-white/[0.03] px-3 py-2">
          <span className="text-xs text-[var(--fv-text-muted)]">Live URL:</span>
          <code className="text-xs text-[var(--fv-accent)]">{lastPublish.public_url}</code>
          <button
            type="button"
            onClick={() => copyLink(lastPublish.public_url)}
            className="text-xs text-[var(--fv-accent)] hover:underline"
          >
            Copy
          </button>
        </div>
      )}

      <button
        type="button"
        disabled={disabled || isPublishing}
        onClick={() => void handlePublish()}
        className={`fv-btn-primary transition-all duration-200 disabled:opacity-50 ${
          fullWidth
            ? "w-full justify-center py-3 text-[15px]"
            : "w-full px-4 py-2.5 text-sm sm:w-auto"
        }`}
      >
        {isPublishing ? "Publishing…" : "Publish to Fivvle"}
      </button>

      {history.length > 0 && (
        <details className="text-xs text-[var(--fv-text-muted)]">
          <summary className="cursor-pointer hover:text-[var(--fv-text-soft)]">
            Publication history ({history.length})
          </summary>
          <ul className="mt-2 space-y-1">
            {history.map((p) => (
              <li key={p.id} className="flex flex-wrap gap-2">
                <a
                  href={p.public_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[var(--fv-accent)]/80 hover:underline"
                >
                  {p.slug}
                </a>
                <span>
                  v{p.output_version}
                  {p.is_current ? " · live" : ""}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
