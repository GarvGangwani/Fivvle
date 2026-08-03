"use client";

import { memo } from "react";
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

function SparkNodeComponent({ data }: NodeProps<SparkNodeData>) {
  const { rawIdea, sparkMetric, isFocused, isRunning, currentSparkVersion } =
    data;
  const ideaSnippet = rawIdea?.trim().slice(0, 60) ?? "";

  return (
    <div
      className={joinClasses(
        "w-64 cursor-pointer rounded-md border-2 border-border-master bg-surface-card p-4 shadow-brutal-md fv-brutal-hover",
        isFocused && "ring-2 ring-brand-primary ring-offset-2",
      )}
    >
      <div
        className={joinClasses(
          "mb-3 flex items-center gap-2",
          isRunning && "text-brand-primary",
        )}
      >
        <div
          className={joinClasses(
            "h-2 w-2 rounded-full",
            isRunning ? "animate-pulse bg-brand-primary" : "bg-ink-primary",
          )}
        />
        <span className="font-label-md text-label-md font-black uppercase">
          PHASE 01: SPARK
        </span>
      </div>

      <h3 className="mb-3 border-b-2 border-ink-primary/10 pb-3 font-headline text-headline-md">
        Capture the raw idea
      </h3>

      {ideaSnippet ? (
        <p className="mb-4 line-clamp-2 font-body text-body-sm text-ink-secondary">
          {ideaSnippet}
          {(rawIdea?.trim().length ?? 0) > 60 ? "..." : ""}
        </p>
      ) : (
        <p className="mb-4 font-body text-body-sm italic text-ink-tertiary">
          Click to add your idea and files.
        </p>
      )}

      <div className="flex items-end justify-between">
        <div>
          <p className="text-mono-sm font-bold uppercase text-ink-primary/50">
            STATUS
          </p>
          <p
            className={joinClasses(
              "font-label-md text-label-md leading-none uppercase",
              sparkMetric.state === "empty" &&
                "bg-ink-primary px-2 py-1 text-brutalist-yellow",
              sparkMetric.state === "drafted" && "text-brand-primary",
              sparkMetric.state === "locked" && "text-ink-tertiary",
            )}
          >
            {sparkMetric.value}
          </p>
          {(currentSparkVersion ?? 0) > 0 ? (
            <p className="mt-1 font-mono text-mono-sm uppercase text-ink-tertiary">
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

export const SparkNode = memo(SparkNodeComponent);
