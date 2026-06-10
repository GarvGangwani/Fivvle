"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Plus, Settings } from "lucide-react";
import { listExperiments } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatRelativeTime } from "@/lib/format-time";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import type { ExperimentSummary } from "@/lib/types";

function getStatusDotColor(status: string): string {
  if (
    status === "RESEARCH_READY" ||
    status === "LANDING_LIVE" ||
    status === "INSIGHT_READY" ||
    status === "COMPLETED"
  ) {
    return "var(--fv-success)";
  }
  if (
    status.startsWith("RESEARCH") ||
    status === "LANDING_GENERATING" ||
    status === "INSIGHT_GENERATING"
  ) {
    return "var(--fv-accent)";
  }
  if (status === "RESEARCH_FAILED" || status === "INSIGHT_FAILED") {
    return "var(--fv-danger)";
  }
  if (status === "LANDING_DRAFT" || status === "REFINING") {
    return "var(--fv-warning)";
  }
  return "var(--fv-text-dim)";
}

function getUserInitial(
  displayName: string | null | undefined,
  email: string | null | undefined,
): string {
  if (displayName) {
    const initial = displayName.trim().charAt(0);
    if (initial) return initial.toUpperCase();
  }
  if (email) return email.charAt(0).toUpperCase();
  return "U";
}

function getUserDisplayName(
  displayName: string | null | undefined,
  email: string | null | undefined,
): string {
  if (displayName?.trim()) return displayName.trim();
  if (email) {
    const local = email.split("@")[0];
    if (local) return local.charAt(0).toUpperCase() + local.slice(1);
  }
  return "Founder";
}

export function getExperimentIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/experiment\/([^/]+)/);
  return match ? match[1] : null;
}

export function ShellSidebar() {
  const pathname = usePathname();
  const activeId = getExperimentIdFromPath(pathname);
  const { user } = useAuth();
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchExperiments = useCallback(async () => {
    try {
      const data = await listExperiments();
      setExperiments(data);
    } catch {
      setExperiments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchExperiments();
  }, [fetchExperiments]);

  const userInitial = getUserInitial(user?.displayName, user?.email);
  const userName = getUserDisplayName(user?.displayName, user?.email);

  return (
    <aside className="hidden h-screen w-[260px] shrink-0 flex-col border-r border-[var(--fv-border)] bg-[var(--fv-surface)] lg:flex">
      <div className="p-4">
        <Link href="/" className="flex items-center gap-2.5 no-underline">
          <div
            className="fv-f-logo"
            style={{ width: 32, height: 32, fontSize: 16 }}
            aria-hidden
          >
            F
          </div>
          <span className="text-base font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
            Fivvle
          </span>
        </Link>

        <Link
          href="/new"
          className="fv-btn-primary mt-5 w-full justify-center py-2.5 text-sm no-underline"
        >
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <p className="mb-2 mt-6 text-[11px] uppercase tracking-[0.1em] text-[var(--fv-text-muted)]">
          Projects
        </p>

        {loading ? (
          <div className="space-y-1">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="fv-skeleton h-14 rounded-lg" />
            ))}
          </div>
        ) : experiments.length === 0 ? (
          <p className="px-1 text-[13px] text-[var(--fv-text-muted)]">
            No projects yet
          </p>
        ) : (
          <div className="space-y-1">
            {experiments.map((experiment) => {
              const isActive = activeId === experiment.id;
              return (
                <Link
                  key={experiment.id}
                  href={`/experiment/${experiment.id}`}
                  className={`fv-sidebar-item block px-3 py-3 no-underline ${
                    isActive ? "fv-sidebar-item-active" : ""
                  }`}
                >
                  <p className="truncate text-[13px] font-medium text-[var(--fv-text)]">
                    {getExperimentDisplayName(experiment)}
                  </p>
                  <div className="mt-1 flex items-center gap-1.5">
                    <span
                      className="h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{
                        background: getStatusDotColor(experiment.status),
                      }}
                    />
                    <span className="text-[11px] text-[var(--fv-text-dim)]">
                      {formatRelativeTime(experiment.updated_at)}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      <div className="border-t border-[var(--fv-border)] p-4">
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--fv-accent-muted)] text-xs font-semibold text-[var(--fv-accent)]"
            aria-hidden
          >
            {userInitial}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium text-[var(--fv-text)]">
              {userName}
            </p>
            {user?.email && (
              <p className="truncate text-[11px] text-[var(--fv-text-muted)]">
                {user.email}
              </p>
            )}
          </div>
          <button
            type="button"
            className="icon-btn shrink-0"
            aria-label="Settings"
            disabled
            title="Settings (coming soon)"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
