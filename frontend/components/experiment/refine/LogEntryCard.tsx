"use client";

export type LogEntry = {
  question: string;
  options: string[];
  selectedIndices: number[];
  customAddedText: string | null;
  rawAnswer: string;
  timestamp: string;
};

type Props = { entry: LogEntry };

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export function LogEntryCard({ entry }: Props) {
  const hasMetadata =
    entry.selectedIndices.length > 0 || Boolean(entry.customAddedText);

  return (
    <div className="border-2 border-border-master bg-surface-elevated p-3">
      <p className="font-body text-body-sm text-ink-secondary mb-3 line-clamp-2">
        {entry.question}
      </p>

      {hasMetadata ? (
        <div className="space-y-1">
          {entry.options.map((opt, i) => {
            const isSelected = entry.selectedIndices.includes(i);
            const letter = String.fromCharCode(65 + i);
            return (
              <div
                key={`${letter}-${opt}`}
                className={`flex items-center gap-2 text-mono-sm font-mono ${
                  isSelected
                    ? "text-ink-primary"
                    : "text-ink-tertiary line-through"
                }`}
              >
                <span className="font-bold">{letter}.</span>
                <span>{opt}</span>
                {isSelected ? (
                  <span
                    className="material-symbols-outlined text-brand-primary"
                    style={{ fontSize: 12 }}
                    aria-hidden="true"
                  >
                    check
                  </span>
                ) : null}
              </div>
            );
          })}
          {entry.customAddedText ? (
            <div className="flex items-start gap-2 text-mono-sm font-mono text-ink-primary mt-1 pt-2 border-t border-border-master/20">
              <span className="font-bold">
                {String.fromCharCode(65 + entry.options.length)}.
              </span>
              <span className="italic flex-1">
                &ldquo;{entry.customAddedText}&rdquo;
              </span>
              <span
                className="material-symbols-outlined text-brand-primary shrink-0"
                style={{ fontSize: 12 }}
                aria-hidden="true"
              >
                check
              </span>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="text-mono-sm font-mono text-ink-secondary italic">
          Answered: &ldquo;{entry.rawAnswer}&rdquo;
        </div>
      )}

      <p className="mt-3 font-mono text-mono-sm text-ink-tertiary uppercase">
        {formatTime(entry.timestamp)} UTC
      </p>
    </div>
  );
}
