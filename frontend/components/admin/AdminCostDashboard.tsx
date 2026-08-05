"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Loader2, Search, TrendingUp, X } from "lucide-react";
import {
  ApiError,
  getAdminCostInsights,
  getAdminDailyCost,
  getAdminExperimentCost,
  getAdminPerProductCost,
  getAdminUserExperimentsCost,
  type CostInsightsResponse,
  type DailyCostRow,
  type ExperimentCostResponse,
  type ProductCostRow,
  type ProviderCostRow,
  type UserCostInsightRow,
  type UserExperimentsCostResponse,
} from "@/lib/api";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { PageHeader } from "@/components/ui/PageHeader";

const DAY_OPTIONS = [7, 30, 90] as const;

function parseUsd(value: string): number {
  const n = Number(value);
  return Number.isNaN(n) ? 0 : n;
}

function formatUsd(value: string | number): string {
  const n = typeof value === "string" ? parseUsd(value) : value;
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(n);
}

function formatShortDate(day: string): string {
  const d = new Date(`${day}T12:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function providerLabel(row: ProviderCostRow): string {
  const source = row.source === "llm" ? "LLM" : "API";
  return `${row.provider} (${source})`;
}

function phaseLabel(phase: string | null): string {
  if (!phase) return "Unscoped";
  return phase.replace(/_/g, " ");
}

function KpiCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: boolean;
}) {
  return (
    <div className="fv-section-card">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
        {label}
      </p>
      <p
        className={`mt-2 text-2xl font-semibold tracking-tight ${
          accent ? "text-accent" : "text-[var(--fv-text)]"
        }`}
      >
        {value}
      </p>
      {hint && (
        <p className="mt-1 text-[12px] text-[var(--fv-text-dim)]">{hint}</p>
      )}
    </div>
  );
}

function VerticalBarChart({
  items,
  maxValue,
  targetValue,
}: {
  items: { key: string; label: string; value: number; sublabel?: string }[];
  maxValue: number;
  targetValue?: number;
}) {
  const scaleMax = Math.max(maxValue, targetValue ?? 0, 0.0001);

  return (
    <div className="flex h-56 items-end justify-center gap-4 sm:gap-8">
      {items.map((item) => {
        const heightPct = Math.max((item.value / scaleMax) * 100, item.value > 0 ? 4 : 0);
        return (
          <div key={item.key} className="flex min-w-0 flex-1 max-w-[88px] flex-col items-center">
            <p className="mb-2 text-center text-[12px] font-medium text-[var(--fv-text)]">
              {formatUsd(item.value)}
            </p>
            <div className="relative flex h-40 w-full items-end justify-center">
              {targetValue !== undefined && (
                <div
                  className="pointer-events-none absolute left-0 right-0 border-t border-dashed border-amber-500/70"
                  style={{ bottom: `${(targetValue / scaleMax) * 100}%` }}
                  aria-hidden
                />
              )}
              <div
                className="w-full max-w-[48px] rounded-t-md bg-accent/85 transition-all"
                style={{ height: `${heightPct}%` }}
                role="img"
                aria-label={`${item.label}: ${formatUsd(item.value)}`}
              />
            </div>
            <p className="mt-2 text-center text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
              {item.label}
            </p>
            {item.sublabel && (
              <p className="mt-0.5 text-center text-[10px] text-[var(--fv-text-dim)]">
                {item.sublabel}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function HorizontalBarList({
  items,
  valueKey,
  labelKey,
  formatValue = formatUsd,
}: {
  items: Record<string, string | number | null>[];
  valueKey: string;
  labelKey: string;
  formatValue?: (value: string | number) => string;
}) {
  const max = Math.max(...items.map((item) => parseUsd(String(item[valueKey]))), 0.0001);

  if (items.length === 0) {
    return (
      <p className="text-sm text-[var(--fv-text-muted)]">No data in this period.</p>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const value = parseUsd(String(item[valueKey]));
        const widthPct = Math.max((value / max) * 100, value > 0 ? 3 : 0);
        const rowKey = String(item.id ?? item[labelKey] ?? index);
        return (
          <div key={rowKey}>
            <div className="mb-1 flex items-center justify-between gap-3 text-[13px]">
              <span className="truncate text-[var(--fv-text)]">
                {String(item[labelKey])}
              </span>
              <span className="shrink-0 font-medium text-[var(--fv-text)]">
                {formatValue(value)}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--fv-border)]/50">
              <div
                className="h-full rounded-full bg-accent/80"
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DailyTrendChart({ rows }: { rows: DailyCostRow[] }) {
  const chronological = useMemo(
    () => [...rows].sort((a, b) => a.day.localeCompare(b.day)),
    [rows],
  );

  if (chronological.length === 0) {
    return (
      <p className="text-sm text-[var(--fv-text-muted)]">No daily spend recorded.</p>
    );
  }

  const maxTotal = Math.max(
    ...chronological.map((row) => parseUsd(row.total_cost_usd)),
    0.0001,
  );

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-4 text-[11px] text-[var(--fv-text-muted)]">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-accent" />
          LLM
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500/80" />
          External APIs
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-amber-400/90" />
          Tavily (subset)
        </span>
      </div>
      <div className="flex h-48 items-end gap-1 overflow-x-auto pb-1">
        {chronological.map((row) => {
          const llm = parseUsd(row.llm_cost_usd);
          const ext = parseUsd(row.external_api_cost_usd);
          const tavily = parseUsd(row.tavily_cost_usd);
          const total = llm + ext;
          const heightPct = Math.max((total / maxTotal) * 100, total > 0 ? 4 : 0);
          const llmPct = total > 0 ? (llm / total) * 100 : 0;
          const extPct = total > 0 ? (ext / total) * 100 : 0;
          const tavilyPct = ext > 0 ? (tavily / ext) * extPct : 0;
          const otherExtPct = extPct - tavilyPct;

          return (
            <div
              key={row.day}
              className="flex min-w-[28px] flex-1 flex-col items-center"
              title={`${row.day}: ${formatUsd(total)} (LLM ${formatUsd(llm)}, ext ${formatUsd(ext)}, Tavily ${formatUsd(tavily)})`}
            >
              <div
                className="flex w-full max-w-[36px] flex-col justify-end overflow-hidden rounded-t-md"
                style={{ height: `${heightPct}%`, minHeight: total > 0 ? "6px" : "0" }}
              >
                {llm > 0 && (
                  <div
                    className="w-full bg-accent/85"
                    style={{ flexGrow: llmPct }}
                  />
                )}
                {otherExtPct > 0 && (
                  <div
                    className="w-full bg-emerald-500/75"
                    style={{ flexGrow: otherExtPct }}
                  />
                )}
                {tavily > 0 && (
                  <div
                    className="w-full bg-amber-400/90"
                    style={{ flexGrow: tavilyPct }}
                  />
                )}
              </div>
              <span className="mt-2 rotate-0 text-[9px] text-[var(--fv-text-dim)] sm:text-[10px]">
                {formatShortDate(row.day)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProductCard({ row }: { row: ProductCostRow }) {
  return (
    <div className="fv-section-card">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
        {row.label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-[var(--fv-text)]">
        {formatUsd(row.total_cost_usd)}
      </p>
      <dl className="mt-3 space-y-1 text-[13px] text-[var(--fv-text-soft)]">
        <div className="flex justify-between gap-2">
          <dt>LLM</dt>
          <dd className="font-medium text-[var(--fv-text)]">
            {formatUsd(row.llm_cost_usd)}{" "}
            <span className="text-[var(--fv-text-dim)]">
              ({row.llm_call_count} calls)
            </span>
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>External APIs</dt>
          <dd className="font-medium text-[var(--fv-text)]">
            {formatUsd(row.external_api_cost_usd)}{" "}
            <span className="text-[var(--fv-text-dim)]">
              ({row.external_api_call_count} calls)
            </span>
          </dd>
        </div>
      </dl>
    </div>
  );
}

function UserCostTable({
  rows,
  selectedUserId,
  onSelectUser,
}: {
  rows: UserCostInsightRow[];
  selectedUserId: string | null;
  onSelectUser: (userId: string) => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-[var(--fv-text-muted)]">No user spend in this period.</p>
    );
  }

  const maxTotal = Math.max(...rows.map((row) => parseUsd(row.total_cost_usd)), 0.0001);

  return (
    <div className="overflow-x-auto">
      <p className="mb-3 text-[12px] text-[var(--fv-text-dim)]">
        Click a user to view their projects and per-phase costs.
      </p>
      <table className="w-full min-w-[640px] text-left text-[13px]">
        <thead>
          <tr className="border-b border-[var(--fv-border)] text-[var(--fv-text-muted)]">
            <th className="py-2 pr-4 font-medium">User</th>
            <th className="py-2 pr-4 font-medium">Projects</th>
            <th className="py-2 pr-4 font-medium">Total</th>
            <th className="py-2 pr-4 font-medium">LLM</th>
            <th className="py-2 pr-4 font-medium">External</th>
            <th className="py-2 font-medium">Share</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const total = parseUsd(row.total_cost_usd);
            const widthPct = Math.max((total / maxTotal) * 100, total > 0 ? 4 : 0);
            const isSelected = selectedUserId === row.user_id;
            return (
              <tr
                key={row.user_id}
                onClick={() => onSelectUser(row.user_id)}
                className={`cursor-pointer border-b border-[var(--fv-border)]/60 text-[var(--fv-text-soft)] transition-colors hover:bg-[var(--fv-border)]/20 ${
                  isSelected ? "bg-accent/10" : ""
                }`}
              >
                <td className="py-3 pr-4">
                  <p className="font-medium text-[var(--fv-text)]">
                    {row.name || row.email}
                  </p>
                  {row.name && (
                    <p className="text-[12px] text-[var(--fv-text-dim)]">{row.email}</p>
                  )}
                </td>
                <td className="py-3 pr-4">{row.experiment_count}</td>
                <td className="py-3 pr-4 font-medium text-[var(--fv-text)]">
                  {formatUsd(row.total_cost_usd)}
                </td>
                <td className="py-3 pr-4">{formatUsd(row.llm_cost_usd)}</td>
                <td className="py-3 pr-4">{formatUsd(row.external_api_cost_usd)}</td>
                <td className="py-3">
                  <div className="h-2 w-28 overflow-hidden rounded-full bg-[var(--fv-border)]/50">
                    <div
                      className="h-full rounded-full bg-accent/80"
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function UserExperimentDrilldown({
  userId,
  days,
  onClose,
}: {
  userId: string;
  days: number;
  onClose: () => void;
}) {
  const [data, setData] = useState<UserExperimentsCostResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminUserExperimentsCost(userId, days);
      setData(result);
      setExpandedIds(new Set());
    } catch {
      setError("Could not load project breakdown for this user.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [userId, days]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleExpanded = (experimentId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(experimentId)) {
        next.delete(experimentId);
      } else {
        next.add(experimentId);
      }
      return next;
    });
  };

  const displayName = data?.name || data?.email || "User";

  return (
    <div className="mt-6 border-t border-[var(--fv-border)] pt-6">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--fv-text)]">
            {displayName}&apos;s projects
          </h3>
          {data?.name && (
            <p className="text-[12px] text-[var(--fv-text-dim)]">{data.email}</p>
          )}
          <p className="mt-1 text-[12px] text-[var(--fv-text-muted)]">
            Spend in the last {days} days, broken down by workflow phase per project.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1.5 text-[var(--fv-text-muted)] transition-colors hover:bg-[var(--fv-border)]/40 hover:text-[var(--fv-text)]"
          aria-label="Close user breakdown"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-8 text-sm text-[var(--fv-text-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading projects…
        </div>
      )}

      {error && (
        <p className="text-sm text-[var(--fv-danger)]">{error}</p>
      )}

      {!loading && !error && data && data.experiments.length === 0 && (
        <p className="text-sm text-[var(--fv-text-muted)]">
          No project spend for this user in the selected period.
        </p>
      )}

      {!loading && !error && data && data.experiments.length > 0 && (
        <div className="space-y-3">
          {data.experiments.map((exp) => {
            const isExpanded = expandedIds.has(exp.experiment_id);
            return (
              <div
                key={exp.experiment_id}
                className="overflow-hidden rounded-lg border border-[var(--fv-border)]/80"
              >
                <button
                  type="button"
                  onClick={() => toggleExpanded(exp.experiment_id)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--fv-border)]/15"
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-[var(--fv-text-muted)]" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-[var(--fv-text)]">
                      {exp.label}
                    </p>
                    <p className="text-[11px] uppercase tracking-wide text-[var(--fv-text-dim)]">
                      {exp.status.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="shrink-0 text-right text-[13px]">
                    <p className="font-medium text-[var(--fv-text)]">
                      {formatUsd(exp.total_cost_usd)}
                    </p>
                    <p className="text-[11px] text-[var(--fv-text-dim)]">
                      LLM {formatUsd(exp.llm_cost_usd)} · Ext{" "}
                      {formatUsd(exp.external_api_cost_usd)}
                    </p>
                  </div>
                </button>

                {isExpanded && (
                  <div className="border-t border-[var(--fv-border)]/60 bg-[var(--fv-bg-soft)]/40 px-4 py-3">
                    {exp.phases.length === 0 ? (
                      <p className="text-[12px] text-[var(--fv-text-muted)]">
                        No phase-level calls in this period.
                      </p>
                    ) : (
                      <table className="w-full text-left text-[12px]">
                        <thead>
                          <tr className="text-[var(--fv-text-muted)]">
                            <th className="pb-2 pr-4 font-medium">Phase</th>
                            <th className="pb-2 pr-4 font-medium">Source</th>
                            <th className="pb-2 pr-4 font-medium">Cost</th>
                            <th className="pb-2 font-medium">Calls</th>
                          </tr>
                        </thead>
                        <tbody>
                          {exp.phases.map((phase) => (
                            <tr
                              key={`${phase.phase}-${phase.source}`}
                              className="border-t border-[var(--fv-border)]/40 text-[var(--fv-text-soft)]"
                            >
                              <td className="py-2 pr-4 text-[var(--fv-text)]">
                                {phase.label}
                              </td>
                              <td className="py-2 pr-4 capitalize">
                                {phase.source === "llm" ? "LLM" : "External API"}
                              </td>
                              <td className="py-2 pr-4 font-medium">
                                {formatUsd(phase.cost_usd)}
                              </td>
                              <td className="py-2">{phase.call_count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AdminCostDashboard() {
  const [days, setDays] = useState<number>(30);
  const [insights, setInsights] = useState<CostInsightsResponse | null>(null);
  const [products, setProducts] = useState<ProductCostRow[]>([]);
  const [dailyRows, setDailyRows] = useState<DailyCostRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [experimentId, setExperimentId] = useState("");
  const [experimentCost, setExperimentCost] =
    useState<ExperimentCostResponse | null>(null);
  const [experimentLoading, setExperimentLoading] = useState(false);
  const [experimentError, setExperimentError] = useState<string | null>(null);

  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [insightsData, productData, dailyData] = await Promise.all([
        getAdminCostInsights(days),
        getAdminPerProductCost(days),
        getAdminDailyCost(days),
      ]);
      setInsights(insightsData);
      setProducts(productData.rows);
      setDailyRows(dailyData.rows);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("You do not have admin access.");
      } else {
        setError("Could not load cost data. Try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  async function handleExperimentLookup(e: React.FormEvent) {
    e.preventDefault();
    const id = experimentId.trim();
    if (!id) return;

    setExperimentLoading(true);
    setExperimentError(null);
    setExperimentCost(null);
    try {
      const data = await getAdminExperimentCost(id);
      setExperimentCost(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setExperimentError("You do not have admin access.");
      } else {
        setExperimentError("Could not load experiment cost. Check the ID.");
      }
    } finally {
      setExperimentLoading(false);
    }
  }

  const summary = insights?.summary;
  const stats = summary?.experiment_stats;
  const target = summary ? parseUsd(summary.target_cost_per_experiment_usd) : 1.5;

  const distributionItems = stats
    ? [
        {
          key: "min",
          label: "Min",
          value: parseUsd(stats.min_cost_usd),
          sublabel: "cheapest project",
        },
        {
          key: "avg",
          label: "Avg",
          value: parseUsd(stats.avg_cost_usd),
          sublabel: "mean per project",
        },
        {
          key: "median",
          label: "Median",
          value: parseUsd(stats.median_cost_usd),
          sublabel: "typical project",
        },
        {
          key: "max",
          label: "Max",
          value: parseUsd(stats.max_cost_usd),
          sublabel: "most expensive",
        },
      ]
    : [];

  const distributionMax = Math.max(
    ...distributionItems.map((item) => item.value),
    target,
    0.0001,
  );

  const tavilyShare =
    summary && parseUsd(summary.total_cost_usd) > 0
      ? (parseUsd(summary.tavily_total_cost_usd) / parseUsd(summary.total_cost_usd)) * 100
      : 0;

  const tavilyGap = summary ? parseUsd(summary.tavily_estimated_gap_usd) : 0;

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <PageHeader
        title="Cost dashboard"
        description="Platform spend, per-user attribution, Tavily usage, and experiment cost distribution."
      />

      {error && (
        <ErrorBanner message={error} className="mb-6" onDismiss={() => setError(null)} />
      )}

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <span className="text-[13px] text-[var(--fv-text-muted)]">Period</span>
        {DAY_OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setDays(option)}
            className={`rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
              days === option
                ? "bg-accent-muted text-accent"
                : "text-[var(--fv-text-muted)] hover:bg-[var(--fv-hover-overlay)]"
            }`}
          >
            {option}d
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-sm text-[var(--fv-text-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading cost data…
        </div>
      ) : (
        <>
          {summary && (
            <section className="mb-10">
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--fv-text)]">
                <TrendingUp className="h-4 w-4 text-accent" />
                Overview
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Total spend" value={formatUsd(summary.total_cost_usd)} />
                <KpiCard
                  label="LLM"
                  value={formatUsd(summary.llm_cost_usd)}
                  hint={`${summary.llm_call_count.toLocaleString()} calls`}
                />
                <KpiCard
                  label="External APIs"
                  value={formatUsd(summary.external_api_cost_usd)}
                  hint={`${summary.external_api_call_count.toLocaleString()} calls`}
                />
                <KpiCard
                  label="Tavily (total)"
                  value={formatUsd(summary.tavily_total_cost_usd)}
                  hint={
                    tavilyGap > 0
                      ? `${formatUsd(summary.tavily_logged_cost_usd)} logged + ${formatUsd(summary.tavily_estimated_gap_usd)} estimated from ${summary.tavily_unlogged_experiment_count} research run(s) without audit rows`
                      : `${summary.tavily_logged_credits.toLocaleString()} credits logged · ${tavilyShare.toFixed(1)}% of total spend`
                  }
                  accent
                />
                <KpiCard
                  label="Active users"
                  value={String(summary.active_user_count)}
                  hint="users with spend"
                />
                <KpiCard
                  label="Projects with spend"
                  value={String(stats?.experiment_count ?? 0)}
                  hint={`target ~${formatUsd(target)} / project`}
                />
                <KpiCard
                  label="Avg / project"
                  value={formatUsd(stats?.avg_cost_usd ?? "0")}
                  hint={
                    stats && parseUsd(stats.avg_cost_usd) > target
                      ? "above target"
                      : "within target band"
                  }
                />
                <KpiCard
                  label="Daily avg"
                  value={formatUsd(parseUsd(summary.total_cost_usd) / days)}
                  hint={`over ${days} days`}
                />
              </div>
            </section>
          )}

          {stats && stats.experiment_count > 0 && (
            <section className="mb-10">
              <h2 className="mb-1 text-sm font-semibold text-[var(--fv-text)]">
                Cost per project distribution
              </h2>
              <p className="mb-4 text-[13px] text-[var(--fv-text-muted)]">
                Min, average, median, and max spend across projects with activity.
                Dashed line marks the ${target.toFixed(2)} MVP target.
              </p>
              <div className="fv-section-card">
                <VerticalBarChart
                  items={distributionItems}
                  maxValue={distributionMax}
                  targetValue={target}
                />
              </div>
            </section>
          )}

          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
              Daily spend trend
            </h2>
            <div className="fv-section-card">
              <DailyTrendChart rows={dailyRows} />
            </div>
          </section>

          {insights && (
            <>
              <section className="mb-10">
                <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
                  Per user
                </h2>
                <div className="fv-section-card">
                  <UserCostTable
                    rows={insights.per_user}
                    selectedUserId={selectedUserId}
                    onSelectUser={setSelectedUserId}
                  />
                  {selectedUserId && (
                    <UserExperimentDrilldown
                      userId={selectedUserId}
                      days={days}
                      onClose={() => setSelectedUserId(null)}
                    />
                  )}
                </div>
              </section>

              <section className="mb-10 grid gap-6 lg:grid-cols-2">
                <div>
                  <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
                    By provider
                  </h2>
                  <div className="fv-section-card">
                    <HorizontalBarList
                      items={insights.per_provider.map((row) => ({
                        id: `${row.provider}-${row.source}`,
                        label: providerLabel(row),
                        value: row.cost_usd,
                      }))}
                      labelKey="label"
                      valueKey="value"
                    />
                  </div>
                </div>
                <div>
                  <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
                    By LLM phase
                  </h2>
                  <div className="fv-section-card">
                    <HorizontalBarList
                      items={insights.per_phase.map((row) => ({
                        id: row.phase ?? "unscoped",
                        label: phaseLabel(row.phase),
                        value: row.llm_cost_usd,
                      }))}
                      labelKey="label"
                      valueKey="value"
                    />
                  </div>
                </div>
              </section>

              {insights.top_experiments.length > 0 && (
                <section className="mb-10">
                  <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
                    Top projects by spend
                  </h2>
                  <div className="fv-section-card">
                    <HorizontalBarList
                      items={insights.top_experiments.map((row) => ({
                        id: row.experiment_id,
                        label: row.label,
                        value: row.total_cost_usd,
                      }))}
                      labelKey="label"
                      valueKey="value"
                    />
                  </div>
                </section>
              )}
            </>
          )}

          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
              By product
            </h2>
            {products.length === 0 ? (
              <p className="text-sm text-[var(--fv-text-muted)]">
                No costs recorded in the last {days} days.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {products.map((row) => (
                  <ProductCard key={row.cost_category} row={row} />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      <section className="mt-10">
        <h2 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
          Per experiment lookup
        </h2>
        <form
          onSubmit={(e) => void handleExperimentLookup(e)}
          className="flex flex-wrap items-center gap-2"
        >
          <input
            type="text"
            value={experimentId}
            onChange={(e) => setExperimentId(e.target.value)}
            placeholder="Experiment UUID"
            className="fv-input min-w-[240px] flex-1 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={experimentLoading || !experimentId.trim()}
            className="fv-btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm disabled:opacity-50"
          >
            {experimentLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Look up
          </button>
        </form>

        {experimentError && (
          <ErrorBanner
            message={experimentError}
            className="mt-4"
            onDismiss={() => setExperimentError(null)}
          />
        )}

        {experimentCost && (
          <div className="mt-4 space-y-4">
            <div className="fv-section-card">
              <p className="text-[11px] uppercase tracking-wide text-[var(--fv-text-muted)]">
                Experiment total
              </p>
              <p className="mt-1 text-xl font-semibold text-[var(--fv-text)]">
                {formatUsd(experimentCost.total_cost_usd)}
              </p>
              <p className="mt-1 text-[13px] text-[var(--fv-text-muted)]">
                {experimentCost.llm_call_count} LLM ·{" "}
                {experimentCost.external_api_call_count} external API calls
              </p>
            </div>
            {experimentCost.products.length > 0 && (
              <div className="grid gap-4 sm:grid-cols-2">
                {experimentCost.products.map((row) => (
                  <ProductCard key={row.cost_category} row={row} />
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
