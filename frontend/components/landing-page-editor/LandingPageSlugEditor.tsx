"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, Pencil, Search, X } from "lucide-react";
import {
  checkLandingPageSlugAvailability,
  patchLandingPage,
  ApiError,
} from "@/lib/api";
import { slugifyProjectName } from "@/lib/published-page";
import { formatPublicLandingHost, getLandingSubdomainSuffix } from "@/lib/landing-host";

type AvailabilityState =
  | { status: "idle" }
  | { status: "checking" }
  | { status: "available"; message: string }
  | { status: "unavailable"; message: string; takenByLive: boolean }
  | { status: "error"; message: string };

interface LandingPageSlugEditorProps {
  experimentId: string;
  currentSlug: string;
  projectName: string;
  /** When true, show a note that the public URL will change. */
  isLive?: boolean;
  /** Omit outer card chrome when nested inside a collapsible section. */
  embedded?: boolean;
  onSlugSaved?: (slug: string) => void;
}

function sanitizeSlugInput(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

export function LandingPageSlugEditor({
  experimentId,
  currentSlug,
  projectName,
  isLive,
  embedded,
  onSlugSaved,
}: LandingPageSlugEditorProps) {
  const publicHost = formatPublicLandingHost(currentSlug);
  const subdomainSuffix = getLandingSubdomainSuffix();
  const [editing, setEditing] = useState(false);
  const [draftSlug, setDraftSlug] = useState(currentSlug);
  const [availability, setAvailability] = useState<AvailabilityState>({
    status: "idle",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editing) {
      setDraftSlug(currentSlug);
    }
  }, [currentSlug, editing]);

  function startEditing() {
    setDraftSlug(currentSlug);
    setAvailability({ status: "idle" });
    setEditing(true);
  }

  function cancelEditing() {
    setDraftSlug(currentSlug);
    setAvailability({ status: "idle" });
    setEditing(false);
  }

  async function handleCheckAvailability() {
    const candidate = sanitizeSlugInput(draftSlug);
    if (candidate.length < 6) {
      setAvailability({
        status: "error",
        message: "URL must be at least 6 characters.",
      });
      return;
    }

    setAvailability({ status: "checking" });
    try {
      const result = await checkLandingPageSlugAvailability(
        experimentId,
        candidate,
      );
      if (result.available) {
        setAvailability({
          status: "available",
          message: result.message ?? "This URL is available.",
        });
      } else {
        setAvailability({
          status: "unavailable",
          message: result.message ?? "This URL is not available.",
          takenByLive: result.taken_by_live,
        });
      }
    } catch (err) {
      setAvailability({
        status: "error",
        message:
          err instanceof ApiError
            ? "Could not check availability. Try again."
            : "Could not check availability.",
      });
    }
  }

  async function handleSave() {
    const candidate = sanitizeSlugInput(draftSlug);
    if (candidate.length < 6) {
      setAvailability({
        status: "error",
        message: "URL must be at least 6 characters.",
      });
      return;
    }

    if (candidate === currentSlug) {
      setEditing(false);
      return;
    }

    setSaving(true);
    try {
      const result = await patchLandingPage(experimentId, { slug: candidate });
      onSlugSaved?.(result.slug);
      setEditing(false);
      setAvailability({ status: "idle" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setAvailability({
          status: "unavailable",
          message: "This URL is already taken. Check availability first.",
          takenByLive: true,
        });
      } else if (err instanceof ApiError && err.status === 400) {
        const body = err.body;
        const detail =
          body &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail: unknown }).detail === "string"
            ? (body as { detail: string }).detail
            : "Invalid URL format.";
        setAvailability({ status: "error", message: detail });
      } else {
        setAvailability({
          status: "error",
          message: "Could not save URL. Try again.",
        });
      }
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div
        className={
          embedded
            ? undefined
            : "rounded-lg border border-[var(--fv-border)] bg-white/[0.02] p-3"
        }
      >
        {!embedded ? (
          <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            Startup URL
          </p>
        ) : null}
        <p
          className={`truncate font-mono text-[13px] text-[var(--fv-accent)]${embedded ? "" : " mt-1"}`}
          title={publicHost}
        >
          {publicHost}
        </p>
        {isLive ? (
          <p className="mt-1 text-[11px] text-[var(--fv-text-dim)]">
            Live — changing the URL updates your public link.
          </p>
        ) : null}
        <div className="mt-2.5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={startEditing}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[12px]"
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit URL
          </button>
          <button
            type="button"
            onClick={startEditing}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[12px]"
          >
            <Search className="h-3.5 w-3.5" />
            Check availability
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        embedded
          ? "space-y-3"
          : "space-y-3 rounded-lg border border-[var(--fv-border)] bg-white/[0.02] p-3"
      }
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
          {embedded ? "Edit URL" : "Edit startup URL"}
        </p>
        <button
          type="button"
          onClick={cancelEditing}
          className="rounded-md p-1 text-[var(--fv-text-muted)] hover:text-[var(--fv-text)]"
          aria-label="Cancel editing URL"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex overflow-hidden rounded-lg border border-[var(--fv-border)] bg-white/[0.03]">
        <input
          type="text"
          value={draftSlug}
          disabled={saving}
          onChange={(e) => {
            setDraftSlug(sanitizeSlugInput(e.target.value));
            setAvailability({ status: "idle" });
          }}
          className="min-w-0 flex-1 bg-transparent px-3 py-2.5 font-mono text-[13px] text-[var(--fv-text)] outline-none"
          aria-label="URL slug"
        />
        <span className="shrink-0 border-l border-[var(--fv-border)] px-3 py-2.5 font-mono text-[12px] text-[var(--fv-text-muted)]">
          {subdomainSuffix}
        </span>
      </div>

      <p className="text-[11px] text-[var(--fv-text-dim)]">
        6–40 characters · lowercase letters, numbers, hyphens
      </p>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={saving}
          onClick={() => setDraftSlug(slugifyProjectName(projectName))}
          className="fv-btn-ghost px-3 py-1.5 text-[12px]"
        >
          Use project name
        </button>
        <button
          type="button"
          disabled={saving || availability.status === "checking"}
          onClick={() => void handleCheckAvailability()}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px]"
        >
          {availability.status === "checking" ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Search className="h-3.5 w-3.5" />
          )}
          Check availability
        </button>
        <button
          type="button"
          disabled={
            saving ||
            draftSlug.length < 6 ||
            availability.status === "unavailable"
          }
          onClick={() => void handleSave()}
          className="fv-btn-primary inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Check className="h-3.5 w-3.5" />
          )}
          Save URL
        </button>
      </div>

      {availability.status === "available" && (
        <p className="text-[12px] text-[var(--fv-success)]">{availability.message}</p>
      )}
      {availability.status === "unavailable" && (
        <p className="text-[12px] text-[var(--fv-danger)]">
          {availability.message}
          {availability.takenByLive ? " (live page)" : ""}
        </p>
      )}
      {availability.status === "error" && (
        <p className="text-[12px] text-[var(--fv-danger)]">{availability.message}</p>
      )}
    </div>
  );
}
