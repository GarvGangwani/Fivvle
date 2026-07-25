"use client";

import type { ExperimentAnalytics, SignupLocationBucket } from "@/lib/types";

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function formatLocation(bucket: SignupLocationBucket): string {
  const parts = [bucket.city, bucket.region, bucket.country].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Unknown";
}

function SourceRows({
  title,
  rows,
}: {
  title: string;
  rows: Record<string, number>;
}) {
  const entries = Object.entries(rows).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    return (
      <div>
        <p className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
          {title}
        </p>
        <p className="mt-1 text-body-sm text-ink-tertiary">None yet</p>
      </div>
    );
  }
  return (
    <div>
      <p className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
        {title}
      </p>
      <ul className="mt-2 space-y-1">
        {entries.map(([source, count]) => (
          <li
            key={source}
            className="flex justify-between gap-4 font-mono text-mono-sm text-ink-secondary"
          >
            <span className="truncate text-ink-primary">{source}</span>
            <span>{count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Props = {
  analytics: ExperimentAnalytics;
};

/** Secondary analytics under the threshold hero — deliberately low visual weight. */
export function SignalWatchingDetail({ analytics }: Props) {
  const locations = analytics.signups_by_location ?? [];

  return (
    <section
      className="border-2 border-border-master bg-surface-elevated p-4 shadow-brutal-sm"
      aria-label="Supporting metrics"
    >
      <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
        Supporting detail
      </p>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
        <div>
          <dt className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
            Conversion
          </dt>
          <dd className="mt-0.5 font-mono text-mono-sm text-ink-secondary">
            {formatPercent(analytics.conversion_rate)}
          </dd>
        </div>
        <div>
          <dt className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
            Unique visitors
          </dt>
          <dd className="mt-0.5 font-mono text-mono-sm text-ink-secondary">
            {analytics.unique_visitors.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
            Days live
          </dt>
          <dd className="mt-0.5 font-mono text-mono-sm text-ink-secondary">
            {analytics.days_live}
          </dd>
        </div>
      </dl>

      <div className="mt-5 grid gap-5 border-t-2 border-border-master pt-4 sm:grid-cols-2">
        <SourceRows title="Views by source" rows={analytics.views_by_source} />
        <SourceRows
          title="Signups by source"
          rows={analytics.signups_by_source}
        />
      </div>

      <div className="mt-5 border-t-2 border-border-master pt-4">
        <p className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
          Signups by location
        </p>
        {locations.length === 0 ? (
          <p className="mt-1 text-body-sm text-ink-tertiary">None yet</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {locations.map((bucket, i) => (
              <li
                key={`${formatLocation(bucket)}-${i}`}
                className="flex justify-between gap-4 font-mono text-mono-sm text-ink-secondary"
              >
                <span className="truncate text-ink-primary">
                  {formatLocation(bucket)}
                </span>
                <span>{bucket.count}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
