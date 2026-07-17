"use client";

import { formatLocalTime } from "./formatLocalTime";

export type LogEntry = {
  question: string;
  options: string[];
  selectedIndices: number[];
  customAddedText: string | null;
  rawAnswer: string;
  timestamp: string;
};

type Props = { entry: LogEntry };

export function LogEntryCard({ entry }: Props) {
  const hasMetadata =
    entry.selectedIndices.length > 0 || Boolean(entry.customAddedText);

  return (
    <div className="rounded-md border-2 border-border-master bg-surface-card p-4 min-h-[240px]">
      <div className="mb-3 pb-3 border-b border-border-master/30">
        <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-1">
          QUESTION
        </div>
        <p className="font-body text-body-sm text-ink-primary leading-relaxed">
          {entry.question}
        </p>
      </div>

      <div>
        <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-2">
          YOUR ANSWER
        </div>
        {hasMetadata ? (
          <div className="space-y-1">
            {entry.options.map((opt, i) => {
              const isSelected = entry.selectedIndices.includes(i);
              const letter = String.fromCharCode(65 + i);
              return (
                <div
                  key={`${letter}-${opt}`}
                  className={`flex items-start gap-2 text-body-sm font-body ${
                    isSelected
                      ? "text-ink-primary"
                      : "text-ink-tertiary line-through opacity-60"
                  }`}
                >
                  <span className="font-mono font-bold shrink-0 mt-0.5">
                    {letter}.
                  </span>
                  <span className="flex-1">{opt}</span>
                </div>
              );
            })}
            {entry.customAddedText ? (
              <div className="flex items-start gap-2 text-body-sm font-body text-ink-primary mt-2 pt-2 border-t border-border-master/20">
                <span className="font-mono font-bold shrink-0 mt-0.5">
                  {String.fromCharCode(65 + entry.options.length)}.
                </span>
                <span className="flex-1 italic">
                  &ldquo;{entry.customAddedText}&rdquo;
                </span>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="font-body text-body-sm text-ink-secondary italic">
            &ldquo;{entry.rawAnswer}&rdquo;
          </p>
        )}
      </div>

      <p className="mt-4 pt-3 border-t border-border-master/30 font-mono text-mono-sm text-ink-tertiary uppercase">
        {formatLocalTime(entry.timestamp)}
      </p>
    </div>
  );
}
