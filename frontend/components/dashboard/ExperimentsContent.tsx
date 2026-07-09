"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { listExperiments, searchExperiments, ApiError } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { ProjectCard } from "./ProjectCard";
import {
  mapStatusToPill,
  type PillState,
} from "./dashboard-helpers";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

type StatusFilter = "ALL" | PillState;
type SortOption = "RECENT" | "OLDEST" | "A-Z";

const STATUS_FILTER_OPTIONS: StatusFilter[] = [
  "ALL",
  "SPARK",
  "REFINING",
  "RESEARCHING",
  "LAUNCHED",
  "COMPLETE",
  "CRITICAL",
];

const DROPDOWN_CLASSES =
  "border-2 border-border-master bg-surface-card shadow-brutal-sm px-4 py-3 " +
  "font-label-md text-label-md uppercase tracking-wider text-ink-primary " +
  "appearance-none pr-10 cursor-pointer " +
  "hover:shadow-brutal-md hover:-translate-x-0.5 hover:-translate-y-0.5 " +
  "transition-all min-w-[140px] focus:border-brand-primary focus:outline-none";

function FilterDropdown({
  value,
  onChange,
  options,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  ariaLabel: string;
}) {
  return (
    <div className="relative">
      <select
        className={DROPDOWN_CLASSES}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label={ariaLabel}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <span
        aria-hidden="true"
        className="material-symbols-outlined pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-primary"
        style={{ fontSize: "18px" }}
      >
        expand_more
      </span>
    </div>
  );
}

export function ExperimentsContent() {
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ExperimentSummary[] | null>(
    null,
  );
  const [searchLoading, setSearchLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [sortBy, setSortBy] = useState<SortOption>("RECENT");

  const fetchExperiments = useCallback(async () => {
    try {
      const experiments = await listExperiments();
      setLoadState({ status: "success", experiments });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setLoadState({
        status: "error",
        message: "Could not load experiments. Please try again.",
      });
    }
  }, []);

  useEffect(() => {
    void fetchExperiments();
  }, [fetchExperiments]);

  useEffect(() => {
    const q = searchQuery.trim();
    if (q.length < 2) {
      setSearchResults(null);
      setSearchLoading(false);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setSearchLoading(true);
      void searchExperiments(q)
        .then(async (hits) => {
          if (cancelled) return;
          if (loadState.status !== "success") {
            setSearchResults([]);
            return;
          }
          const idSet = new Set(hits.map((h) => h.id));
          const matched = loadState.experiments.filter((exp) =>
            idSet.has(exp.id),
          );
          setSearchResults(matched);
        })
        .catch(() => {
          if (!cancelled) setSearchResults([]);
        })
        .finally(() => {
          if (!cancelled) setSearchLoading(false);
        });
    }, 200);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchQuery, loadState]);

  const displayed = useMemo(() => {
    if (loadState.status !== "success") return [];
    const base =
      searchResults !== null ? searchResults : loadState.experiments;

    const filtered =
      statusFilter === "ALL"
        ? base
        : base.filter((exp) => mapStatusToPill(exp.status) === statusFilter);

    const sorted = [...filtered];
    if (sortBy === "RECENT") {
      sorted.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );
    } else if (sortBy === "OLDEST") {
      sorted.sort(
        (a, b) =>
          new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      );
    } else {
      sorted.sort((a, b) =>
        (a.name ?? a.raw_idea).localeCompare(b.name ?? b.raw_idea),
      );
    }
    return sorted;
  }, [loadState, searchResults, statusFilter, sortBy]);

  if (loadState.status === "loading") {
    return (
      <div className="py-8">
        <div className="mb-8 h-10 w-64 animate-pulse bg-surface-elevated motion-reduce:animate-none" />
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-64 animate-pulse bg-surface-elevated motion-reduce:animate-none"
            />
          ))}
        </div>
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex items-center justify-center py-20">
        <p
          role="alert"
          className="border-2 border-status-critical bg-surface-card px-6 py-4 font-body-md text-body-md text-status-critical"
        >
          {loadState.message}
        </p>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="font-display text-display-lg uppercase text-ink-primary">
          YOUR EXPERIMENTS
        </h1>
        <Link
          href="/new"
          className={`${marketingButtonClass} inline-flex shrink-0 bg-brand-primary px-6 py-3 font-label-md text-label-md uppercase text-ink-inverse no-underline`}
        >
          START NEW VALIDATION
        </Link>
      </div>

      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <label className="relative block w-full max-w-md flex-1">
          <span className="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-brand-primary">
            auto_awesome
          </span>
          <input
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search experiments by title, idea, or tag..."
            className="w-full border-2 border-border-master bg-surface-card py-3 pl-11 pr-4 font-body-md text-body-md text-ink-primary placeholder:text-ink-tertiary focus:border-brand-primary focus:outline-none"
          />
        </label>
        <div className="flex items-center gap-4">
          <FilterDropdown
            value={statusFilter}
            onChange={(value) => setStatusFilter(value as StatusFilter)}
            options={STATUS_FILTER_OPTIONS.map((option) => ({
              value: option,
              label: option,
            }))}
            ariaLabel="Filter by status"
          />
          <FilterDropdown
            value={sortBy}
            onChange={(value) => setSortBy(value as SortOption)}
            options={[
              { value: "RECENT", label: "RECENT" },
              { value: "OLDEST", label: "OLDEST" },
              { value: "A-Z", label: "A-Z" },
            ]}
            ariaLabel="Sort experiments"
          />
        </div>
      </div>

      {searchLoading ? (
        <p className="mb-4 font-body-md text-body-md text-ink-secondary">
          Searching...
        </p>
      ) : null}

      {displayed.length === 0 ? (
        <div className="border-2 border-border-master bg-surface-card p-10 text-center shadow-brutal-md">
          <p className="font-headline text-headline-md text-ink-primary">
            No experiments match your filters
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {displayed.map((experiment) => (
            <ProjectCard key={experiment.id} experiment={experiment} />
          ))}
        </div>
      )}

      <div className="mt-10 border-t-2 border-border-master pt-6">
        <Link
          href="/archived"
          className="font-label-md text-label-md uppercase text-ink-secondary no-underline hover:text-ink-primary"
        >
          VIEW ARCHIVED EXPERIMENTS →
        </Link>
      </div>
    </div>
  );
}
