"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

export type ActNodeData = {
  index: string;
  actName: string;
  title: string;
  icon: string;
  metricLabel: string;
  metricValue: string;
  validationPercent?: number;
  isRunning: boolean;
  isFocused?: boolean;
  isLocked?: boolean;
  unlockRequirement?: string;
  /** @deprecated Prefer isLocked — kept for temporary back-compat */
  isDisabled?: boolean;
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

function ActNodeComponent({ data }: NodeProps<ActNodeData>) {
  const isActive = data.isRunning;
  const isLocked = Boolean(data.isLocked ?? data.isDisabled);
  const showFocusRing = !isLocked && (Boolean(data.isFocused) || isActive);

  return (
    <div
      className={joinClasses(
        "group z-20 w-64 rounded-md border-2 border-border-master bg-surface-card p-4 shadow-brutal-md transition-[border-color,box-shadow,background-color,opacity]",
        !isLocked && "cursor-grab fv-brutal-hover",
        isLocked && "cursor-not-allowed opacity-40",
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
          PHASE {data.index}: {data.actName}
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
            {isLocked ? "LOCKED" : data.metricValue}
          </p>
        </div>
        <span
          className={joinClasses(
            "material-symbols-outlined text-ink-primary/20",
            !isLocked && "group-hover:text-ink-primary",
          )}
          aria-hidden="true"
        >
          {isLocked ? "lock" : data.icon}
        </span>
      </div>

      {data.validationPercent !== undefined && !isLocked ? (
        <div className="mt-4 bg-ink-primary/5 p-2">
          <span className="text-mono-sm font-black uppercase">
            {data.validationPercent}% VALIDATED
          </span>
        </div>
      ) : null}

      {data.isStale && !isLocked ? (
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
