"use client";

import { Handle, Position, type NodeProps } from "reactflow";

export type SparkMetricState = "empty" | "drafted" | "locked";

export type SparkNodeData = {
  rawIdea: string | null;
  sparkMetric: { value: string; state: SparkMetricState };
  isFocused: boolean;
  isRunning: boolean;
  currentSparkVersion?: number;
};

function joinClasses(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function SparkNode({ data }: NodeProps<SparkNodeData>) {
  const { rawIdea, sparkMetric, isFocused, isRunning, currentSparkVersion } =
    data;
  const ideaSnippet = rawIdea?.trim().slice(0, 60) ?? "";

  return (
    <div
      className={joinClasses(
        "rounded-md border-2 border-border-master bg-surface-card shadow-brutal-md w-64 p-4 cursor-pointer fv-brutal-hover",
        isFocused && "ring-2 ring-brand-primary ring-offset-2",
      )}
    >
      <div
        className={joinClasses(
          "flex items-center gap-2 mb-3",
          isRunning && "text-brand-primary",
        )}
      >
        <div
          className={joinClasses(
            "w-2 h-2 rounded-full",
            isRunning ? "bg-brand-primary animate-pulse" : "bg-ink-primary",
          )}
        />
        <span className="font-label-md text-label-md uppercase font-black">
          PHASE 01: SPARK
        </span>
      </div>

      <h3 className="font-headline text-headline-md mb-3 pb-3 border-b-2 border-ink-primary/10">
        Capture the raw idea
      </h3>

      {ideaSnippet ? (
        <p className="font-body text-body-sm text-ink-secondary mb-4 line-clamp-2">
          {ideaSnippet}
          {(rawIdea?.trim().length ?? 0) > 60 ? "..." : ""}
        </p>
      ) : (
        <p className="font-body text-body-sm text-ink-tertiary italic mb-4">
          Click to add your idea and files.
        </p>
      )}

      <div className="flex justify-between items-end">
        <div>
          <p className="text-mono-sm font-bold text-ink-primary/50 uppercase">
            STATUS
          </p>
          <p
            className={joinClasses(
              "font-label-md text-label-md leading-none uppercase",
              sparkMetric.state === "empty" &&
                "text-brutalist-yellow bg-ink-primary px-2 py-1",
              sparkMetric.state === "drafted" && "text-brand-primary",
              sparkMetric.state === "locked" && "text-ink-tertiary",
            )}
          >
            {sparkMetric.value}
          </p>
          {(currentSparkVersion ?? 0) > 0 ? (
            <p className="font-mono text-mono-sm text-ink-tertiary uppercase mt-1">
              v{currentSparkVersion}
            </p>
          ) : null}
        </div>
        <span
          className="material-symbols-outlined text-ink-primary/20"
          aria-hidden="true"
        >
          bolt
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        id="out"
        style={{
          background: "transparent",
          border: "none",
          width: 1,
          height: 1,
          pointerEvents: "none",
        }}
      />
    </div>
  );
}
