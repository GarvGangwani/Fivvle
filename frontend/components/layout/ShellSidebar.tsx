"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Archive,
  BarChart3,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Sun,
  Ticket,
} from "lucide-react";
import { listExperiments } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { getUserDisplayName } from "@/lib/user-avatar";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { EXPERIMENTS_CHANGED_EVENT } from "@/lib/experiment-events";
import { formatRelativeTime } from "@/lib/format-time";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { useSidebar } from "@/lib/sidebar-context";
import { usePreferences } from "@/lib/preferences-context";
import type { ExperimentSummary } from "@/lib/types";

function getStatusDotColor(status: string): string {
  if (
    status === "RESEARCH_READY" ||
    status === "LANDING_LIVE" ||
    status === "INSIGHT_READY"
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

function projectInitial(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "?";
  return trimmed.charAt(0).toUpperCase();
}

export function getExperimentIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/experiment\/([^/]+)/);
  return match ? match[1] : null;
}

export function ShellSidebar() {
  const pathname = usePathname();
  const activeId = getExperimentIdFromPath(pathname);
  const { user, isAdmin } = useAuth();
  const { collapsed, toggle } = useSidebar();
  const { resolvedTheme, setThemeMode } = usePreferences();
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

  useEffect(() => {
    const onChanged = () => {
      void fetchExperiments();
    };
    window.addEventListener(EXPERIMENTS_CHANGED_EVENT, onChanged);
    return () => window.removeEventListener(EXPERIMENTS_CHANGED_EVENT, onChanged);
  }, [fetchExperiments]);

  const userName = getUserDisplayName(user?.displayName, user?.email);
  const switchToLight = resolvedTheme === "dark";
  const themeToggleLabel = switchToLight ? "Switch to Light" : "Switch to Dark";

  const toggleTheme = () => {
    setThemeMode(switchToLight ? "light" : "dark");
  };

  return (
    <aside
      className={`fv-shell-sidebar sticky top-0 hidden h-screen shrink-0 flex-col self-start border-r border-[var(--fv-border)] bg-[var(--fv-surface)] lg:flex ${
        collapsed ? "fv-shell-sidebar-collapsed" : "fv-shell-sidebar-expanded"
      }`}
      aria-label="Project navigation"
      aria-expanded={!collapsed}
    >
      <div className={collapsed ? "p-3" : "p-4"}>
        <div
          className={`flex items-center ${
            collapsed ? "flex-col gap-3" : "justify-between gap-2"
          }`}
        >
          <Link
            href="/"
            className={`flex items-center no-underline ${
              collapsed ? "justify-center" : "min-w-0 gap-2.5"
            }`}
            title="Fivvle home"
          >
            <div
              className="fv-f-logo shrink-0"
              style={{ width: 32, height: 32, fontSize: 16 }}
              aria-hidden
            >
              F
            </div>
            {!collapsed && (
              <span className="truncate text-base font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
                Fivvle
              </span>
            )}
          </Link>

          <button
            type="button"
            onClick={toggle}
            className="fv-icon-btn shrink-0"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>

        <Link
          href="/new"
          className={`fv-btn-primary mt-5 text-sm no-underline ${
            collapsed
              ? "mx-auto flex h-10 w-10 items-center justify-center p-0"
              : "w-full justify-center py-2.5"
          }`}
          title="New project"
        >
          <Plus className="h-4 w-4 shrink-0" />
          {!collapsed && <span>New Project</span>}
        </Link>
      </div>

      <div
        className={`flex-1 overflow-x-hidden overflow-y-auto pb-4 ${
          collapsed ? "px-2" : "px-4"
        }`}
      >
        {!collapsed && (
          <p className="mb-2 mt-6 text-[11px] uppercase tracking-[0.1em] text-[var(--fv-text-muted)]">
            Projects
          </p>
        )}

        {loading ? (
          <div className="space-y-1">
            {Array.from({ length: collapsed ? 3 : 4 }).map((_, i) => (
              <div
                key={i}
                className={`fv-skeleton rounded-lg ${
                  collapsed ? "mx-auto h-10 w-10" : "h-14"
                }`}
              />
            ))}
          </div>
        ) : experiments.length === 0 ? (
          !collapsed && (
            <p className="px-1 text-[13px] text-[var(--fv-text-muted)]">
              No projects yet
            </p>
          )
        ) : (
          <div className={collapsed ? "space-y-1.5" : "space-y-1"}>
            {experiments.map((experiment) => {
              const isActive = activeId === experiment.id;
              const displayName = getExperimentDisplayName(experiment);

              if (collapsed) {
                return (
                  <Link
                    key={experiment.id}
                    href={`/experiment/${experiment.id}`}
                    title={displayName}
                    className={`relative mx-auto flex h-10 w-10 items-center justify-center rounded-lg text-[13px] font-semibold no-underline transition-colors ${
                      isActive
                        ? "bg-[color-mix(in_srgb,var(--fv-accent)_14%,transparent)] text-[var(--fv-accent)] ring-1 ring-[color-mix(in_srgb,var(--fv-accent)_35%,transparent)]"
                        : "text-[var(--fv-text-soft)] hover:bg-[var(--fv-hover-overlay)]"
                    }`}
                  >
                    {projectInitial(displayName)}
                    <span
                      className="absolute bottom-1 right-1 h-1.5 w-1.5 rounded-full ring-2 ring-[var(--fv-surface)]"
                      style={{
                        background: getStatusDotColor(experiment.status),
                      }}
                      aria-hidden
                    />
                  </Link>
                );
              }

              return (
                <Link
                  key={experiment.id}
                  href={`/experiment/${experiment.id}`}
                  className={`fv-sidebar-item block px-3 py-3 no-underline ${
                    isActive ? "fv-sidebar-item-active" : ""
                  }`}
                >
                  <p className="truncate text-[13px] font-medium text-[var(--fv-text)]">
                    {displayName}
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

        <Link
          href="/archived"
          title="Archived projects"
          className={`fv-sidebar-item flex items-center text-[13px] no-underline ${
            collapsed
              ? "mx-auto mt-4 h-10 w-10 justify-center rounded-lg p-0"
              : "mt-4 gap-2 px-3 py-2.5"
          } ${pathname === "/archived" ? "fv-sidebar-item-active" : ""}`}
        >
          <Archive className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
          {!collapsed && (
            <span className="text-[var(--fv-text-muted)]">Archived</span>
          )}
        </Link>

        {isAdmin && (
          <>
            <Link
              href="/admin/cost"
              title="Admin cost dashboard"
              className={`fv-sidebar-item flex items-center text-[13px] no-underline ${
                collapsed
                  ? "mx-auto mt-1.5 h-10 w-10 justify-center rounded-lg p-0"
                  : "mt-1.5 gap-2 px-3 py-2.5"
              } ${
                pathname.startsWith("/admin/cost") ? "fv-sidebar-item-active" : ""
              }`}
            >
              <BarChart3 className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
              {!collapsed && (
                <span className="text-[var(--fv-text-muted)]">Cost</span>
              )}
            </Link>
            <Link
              href="/admin/coupons"
              title="Admin coupon management"
              className={`fv-sidebar-item flex items-center text-[13px] no-underline ${
                collapsed
                  ? "mx-auto mt-1.5 h-10 w-10 justify-center rounded-lg p-0"
                  : "mt-1.5 gap-2 px-3 py-2.5"
              } ${
                pathname.startsWith("/admin/coupons")
                  ? "fv-sidebar-item-active"
                  : ""
              }`}
            >
              <Ticket className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
              {!collapsed && (
                <span className="text-[var(--fv-text-muted)]">Coupons</span>
              )}
            </Link>
          </>
        )}
      </div>

      <div
        className={`border-t border-[var(--fv-border)] ${
          collapsed ? "p-3" : "p-4"
        }`}
      >
        <button
          type="button"
          onClick={toggleTheme}
          title={themeToggleLabel}
          aria-label={themeToggleLabel}
          className={`fv-sidebar-item flex w-full items-center text-[13px] ${
            collapsed
              ? "mx-auto mb-3 h-10 w-10 justify-center rounded-lg p-0"
              : "mb-3 gap-2 px-3 py-2.5"
          }`}
        >
          {switchToLight ? (
            <Sun className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
          ) : (
            <Moon className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
          )}
          {!collapsed && (
            <span className="text-[var(--fv-text-muted)]">{themeToggleLabel}</span>
          )}
        </button>
        {collapsed ? (
          <div title={userName} aria-label={userName}>
            <UserAvatar
              displayName={user?.displayName}
              email={user?.email}
              photoUrl={user?.photoURL}
              className="mx-auto"
            />
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <UserAvatar
              displayName={user?.displayName}
              email={user?.email}
              photoUrl={user?.photoURL}
            />
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
          </div>
        )}
      </div>
    </aside>
  );
}
