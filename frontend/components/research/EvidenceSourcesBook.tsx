"use client";

import { ExternalLink } from "lucide-react";
import type { Citation, ValidationReport } from "@/lib/types";

interface SourceGroup {
  domain: string;
  citations: Citation[];
}

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function buildSourceGroups(report: ValidationReport): SourceGroup[] {
  const seen = new Set<string>();
  const byDomain = new Map<string, Citation[]>();

  const collect = (citations: Citation[]) => {
    for (const citation of citations) {
      const key = citation.url || citation.title;
      if (seen.has(key)) continue;
      seen.add(key);
      const domain = citation.source_domain?.trim() || "Other sources";
      const group = byDomain.get(domain) ?? [];
      group.push(citation);
      byDomain.set(domain, group);
    }
  };

  for (const qf of report.questions_and_findings) {
    for (const finding of qf.findings) {
      collect(finding.citations);
    }
  }
  for (const competitor of report.competitors) {
    collect(competitor.citations);
  }

  const groups = Array.from(byDomain.entries()).map(([domain, citations]) => ({
    domain,
    citations,
  }));
  groups.sort(
    (a, b) =>
      b.citations.length - a.citations.length ||
      a.domain.localeCompare(b.domain),
  );
  return groups;
}

export function EvidenceSourcesBook({ report }: { report: ValidationReport }) {
  const groups = buildSourceGroups(report);

  return (
    <section aria-labelledby="evidence-sources-heading" className="space-y-3">
      <h2
        id="evidence-sources-heading"
        className="font-mono text-mono-md uppercase text-ink-secondary"
      >
        Sources
      </h2>

      {groups.length === 0 ? (
        <div className="border-2 border-border-master bg-surface-card p-4 font-mono text-mono-sm uppercase text-ink-tertiary shadow-brutal-sm">
          No sources cited in this report.
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => (
            <div
              key={group.domain}
              className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm"
            >
              <div className="mb-2 flex items-baseline justify-between gap-2">
                <h3 className="font-mono text-mono-md uppercase text-ink-primary">
                  {group.domain}
                </h3>
                <span className="font-mono text-mono-sm text-ink-tertiary">
                  {group.citations.length}
                </span>
              </div>
              <ul className="space-y-1.5">
                {group.citations.map((citation) => (
                  <li key={citation.url || citation.title}>
                    {isSafeHttpUrl(citation.url) ? (
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-start gap-1 text-sm text-accent underline underline-offset-2"
                      >
                        <span>{citation.title}</span>
                        <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 opacity-70" />
                      </a>
                    ) : (
                      <span className="text-sm text-ink-secondary">
                        {citation.title}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
