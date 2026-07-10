"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { searchExperiments } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { useSearchModal } from "./search-modal-context";

function highlightSnippet(snippet: string, query: string) {
  const idx = snippet.toLowerCase().indexOf(query.toLowerCase());
  if (idx < 0) return snippet;
  return (
    <>
      {snippet.slice(0, idx)}
      <mark className="bg-brutalist-yellow text-ink-primary">
        {snippet.slice(idx, idx + query.length)}
      </mark>
      {snippet.slice(idx + query.length)}
    </>
  );
}

export function GlobalSearchModal() {
  const router = useRouter();
  const { open, closeSearch } = useSearchModal();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setDebounced("");
      setResults([]);
      return;
    }
  }, [open]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query.trim()), 200);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!open || debounced.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    void searchExperiments(debounced)
      .then((items) => {
        if (!cancelled) setResults(items.slice(0, 10));
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [debounced, open]);

  if (!open) return null;

  function goToExperiment(id: string) {
    closeSearch();
    router.push(`/experiment/${id}`);
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-ink-primary/60 px-gutter pt-24"
      role="presentation"
      onClick={closeSearch}
    >
      <div
        className="w-full max-w-2xl border-2 border-border-master bg-surface-card p-6 shadow-brutal-lg"
        role="dialog"
        aria-modal="true"
        aria-label="Search experiments"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b-2 border-border-master pb-4">
          <span className="material-symbols-outlined text-brand-primary" aria-hidden>
            auto_awesome
          </span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search experiments..."
            autoFocus
            aria-label="Search experiments"
            className="min-w-0 flex-1 border-0 bg-transparent font-body-md text-body-md text-ink-primary placeholder:text-ink-tertiary focus:outline-none"
          />
          <button
            type="button"
            onClick={closeSearch}
            className="font-mono text-mono-sm uppercase text-ink-tertiary"
            aria-label="Close search"
          >
            Esc
          </button>
        </div>

        <div className="mt-4 max-h-[50vh] overflow-y-auto">
          {loading ? (
            <p className="font-body-md text-body-md text-ink-secondary">Searching...</p>
          ) : debounced.length >= 2 && results.length === 0 ? (
            <p className="font-body-md text-body-md text-ink-secondary">
              No results for &quot;{debounced}&quot;
            </p>
          ) : (
            <ul className="space-y-2">
              {results.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => goToExperiment(item.id)}
                    className="group flex w-full items-start justify-between gap-4 border-2 border-transparent px-3 py-3 text-left transition-colors hover:border-border-master hover:bg-surface-muted"
                  >
                    <div className="min-w-0">
                      <p className="font-headline text-headline-md text-ink-primary">
                        {item.title}
                      </p>
                      <p className="mt-1 font-body-sm text-body-sm text-ink-secondary">
                        {highlightSnippet(item.snippet, debounced)}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <StatusBadge status={item.status} />
                      <span className="font-mono text-mono-sm uppercase text-ink-tertiary opacity-0 group-hover:opacity-100">
                        ↵
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
