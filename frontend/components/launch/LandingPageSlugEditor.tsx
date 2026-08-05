"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, Pencil, Search, X } from "lucide-react";
import {
  checkLandingPageSlugAvailability,
  patchLandingPage,
  ApiError,
} from "@/lib/api";
import { slugifyProjectName } from "@/lib/published-page";
import {
  formatPublicLandingHost,
  getLandingSubdomainSuffix,
} from "@/lib/landing-host";

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

const ghostButtonClass =
  "inline-flex items-center gap-1.5 border-2 border-border-master bg-surface-card px-3 py-2 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-brutal-sm";

const primaryButtonClass =
  "inline-flex items-center gap-1.5 border-2 border-border-master bg-accent px-3 py-2 font-label-md text-label-sm uppercase tracking-wider text-ink-inverse shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-brutal-sm";

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

  const cardClass = embedded
    ? undefined
    : "border-2 border-border-master bg-surface-card p-3 shadow-brutal-sm";

  if (!editing) {
    return (
      <div className={cardClass}>
        {!embedded ? (
          <p className="font-label-md text-label-sm uppercase text-ink-tertiary">
            Startup URL
          </p>
        ) : null}
        <p
          className={`truncate font-mono text-body-sm text-accent${embedded ? "" : " mt-1"}`}
          title={publicHost}
        >
          {publicHost}
        </p>
        {isLive ? (
          <p className="mt-1 font-mono text-mono-sm uppercase text-ink-tertiary">
            Live — changing the URL updates your public link.
          </p>
        ) : null}
        <div className="mt-2.5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={startEditing}
            className={ghostButtonClass}
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit URL
          </button>
          <button
            type="button"
            onClick={startEditing}
            className={ghostButtonClass}
          >
            <Search className="h-3.5 w-3.5" />
            Check availability
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={embedded ? "space-y-3" : `space-y-3 ${cardClass ?? ""}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="font-label-md text-label-sm uppercase text-ink-tertiary">
          {embedded ? "Edit URL" : "Edit startup URL"}
        </p>
        <button
          type="button"
          onClick={cancelEditing}
          className="border-2 border-border-master bg-surface-card p-1 text-ink-tertiary transition-colors hover:text-ink-primary"
          aria-label="Cancel editing URL"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex overflow-hidden border-2 border-border-master bg-surface-elevated focus-within:border-accent">
        <input
          type="text"
          value={draftSlug}
          disabled={saving}
          onChange={(e) => {
            setDraftSlug(sanitizeSlugInput(e.target.value));
            setAvailability({ status: "idle" });
          }}
          className="min-w-0 flex-1 bg-transparent px-3 py-2.5 font-mono text-body-sm text-ink-primary outline-none"
          aria-label="URL slug"
        />
        <span className="shrink-0 border-l-2 border-border-master px-3 py-2.5 font-mono text-mono-sm text-ink-tertiary">
          {subdomainSuffix}
        </span>
      </div>

      <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
        6–40 characters · lowercase letters, numbers, hyphens
      </p>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={saving}
          onClick={() => setDraftSlug(slugifyProjectName(projectName))}
          className={ghostButtonClass}
        >
          Use project name
        </button>
        <button
          type="button"
          disabled={saving || availability.status === "checking"}
          onClick={() => void handleCheckAvailability()}
          className={ghostButtonClass}
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
          className={primaryButtonClass}
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
        <p className="font-mono text-mono-sm text-status-success">
          {availability.message}
        </p>
      )}
      {availability.status === "unavailable" && (
        <p className="font-mono text-mono-sm text-status-critical">
          {availability.message}
          {availability.takenByLive ? " (live page)" : ""}
        </p>
      )}
      {availability.status === "error" && (
        <p className="font-mono text-mono-sm text-status-critical">
          {availability.message}
        </p>
      )}
    </div>
  );
}
