"use client";

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
};

function joinClasses(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function ActNode({ data }: NodeProps<ActNodeData>) {
  const isActive = data.isRunning;

  return (
    <div
      className={joinClasses(
        "group border-2 border-border-master bg-surface-card shadow-brutal-md w-64 p-4 cursor-grab transition-all z-20",
        "hover:bg-brand-primary-soft hover:shadow-brutal-lg hover:-translate-x-0.5 hover:-translate-y-0.5",
        isActive && "ring-2 ring-brand-primary ring-offset-2",
      )}
    >
      <div className={joinClasses("flex items-center gap-2 mb-3", isActive && "text-brand-primary")}>
        <div
          className={joinClasses(
            "w-2 h-2 rounded-full",
            isActive ? "bg-brand-primary animate-pulse" : "bg-ink-primary",
          )}
        />
        <span className="font-label-md text-label-md uppercase font-black">
          PHASE {data.index}: {data.actName}
        </span>
      </div>

      <h3 className="font-headline text-headline-md mb-3 pb-3 border-b-2 border-ink-primary/10">
        {data.title}
      </h3>

      <div className="flex justify-between items-end">
        <div>
          <p className="text-mono-sm font-bold text-ink-primary/50 uppercase">
            {data.metricLabel}
          </p>
          <p className="font-headline text-headline-md leading-none">{data.metricValue}</p>
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
