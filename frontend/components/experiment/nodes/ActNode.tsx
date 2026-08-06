"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

export type ActNodeData = {
  actName: string;
  title: string;
  icon: string;
  metricLabel: string;
  metricValue: string;
  validationPercent?: number;
  isRunning: boolean;
  isFocused?: boolean;
  isStale?: boolean;
  basedOnVersion?: number | null;
  currentSparkVersion?: number;
  canRerun?: boolean;
  rerunning?: boolean;
  onRerun?: () => void;
};

function joinClasses(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/**
 * Canvas phase satellite. Only mounted once the phase is revealed (see
 * getPhaseRevealState), so there is no locked variant — the reveal animation
 * runs on mount, covering both initial load and a phase unlocking live.
 */
function ActNodeComponent({ data }: NodeProps<ActNodeData>) {
  const isActive = data.isRunning;
  const showFocusRing = Boolean(data.isFocused) || isActive;

  return (
    <div
      className={joinClasses(
        "fv-node-reveal group z-20 w-64 cursor-grab rounded-md border-2 border-border-master bg-surface-card p-4 shadow-brutal-md transition-[border-color,box-shadow,background-color,opacity] fv-brutal-hover",
        showFocusRing && "ring-2 ring-accent-ring ring-offset-2",
      )}
    >
      <div
        className={joinClasses(
          "mb-3 flex items-center gap-2",
          isActive && "text-accent",
        )}
      >
        <div
          className={joinClasses(
            "h-2 w-2 rounded-full",
            isActive ? "animate-pulse bg-accent" : "bg-ink-primary",
          )}
        />
        <span className="font-label-md text-label-md font-black uppercase">
          {data.actName}
        </span>
      </div>

      <h3 className="mb-3 border-b-2 border-ink-primary/10 pb-3 font-headline text-headline-md">
        {data.title}
      </h3>

      <div className="flex items-end justify-between">
        <div>
          <p className="text-mono-sm font-bold uppercase text-ink-primary/50">
            {data.metricLabel}
          </p>
          <p className="font-headline text-headline-md leading-none uppercase">
            {data.metricValue}
          </p>
        </div>
        <span
          className="material-symbols-outlined text-ink-primary/20 group-hover:text-ink-primary"
          aria-hidden="true"
        >
          {data.icon}
        </span>
      </div>

      {data.validationPercent !== undefined ? (
        <div className="mt-4 bg-ink-primary/5 p-2">
          <span className="text-mono-sm font-black uppercase">
            {data.validationPercent}% VALIDATED
          </span>
        </div>
      ) : null}

      {data.isStale ? (
        <div className="-mx-4 -mb-4 mt-3 border-t-2 border-brutalist-yellow bg-brutalist-yellow/20 p-2">
          <div className="flex items-center gap-2 px-4">
            <span
              className="material-symbols-outlined text-ink-primary"
              style={{ fontSize: 14 }}
              aria-hidden="true"
            >
              info
            </span>
            <span className="font-mono text-mono-sm uppercase text-ink-primary">
              BASED ON v{data.basedOnVersion} · CURRENT IS v
              {data.currentSparkVersion}
            </span>
          </div>
          {data.canRerun ? (
            <div className="px-4 pb-3 pt-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  data.onRerun?.();
                }}
                disabled={data.rerunning}
                className="w-full rounded-sm border-2 border-border-master bg-accent px-3 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-sm transition-[box-shadow,opacity] hover:shadow-brutal-md disabled:opacity-50"
              >
                {data.rerunning
                  ? "RE-RUNNING..."
                  : `RE-RUN WITH v${data.currentSparkVersion}`}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

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

export const ActNode = memo(ActNodeComponent);
