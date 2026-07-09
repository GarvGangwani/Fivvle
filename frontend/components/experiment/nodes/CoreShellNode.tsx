"use client";

import { Handle, Position, type NodeProps } from "reactflow";

type CoreShellData = {
  projectName: string;
  refinedIdea: string | null;
  rawIdea: string | null;
  phasesComplete: number;
};

function coreIdeaText(data: CoreShellData): string {
  if (data.refinedIdea) return data.refinedIdea;
  if (data.rawIdea) {
    const trimmed = data.rawIdea.trim();
    if (trimmed.length <= 120) return trimmed;
    return `${trimmed.slice(0, 120)}...`;
  }
  return "Refined idea will appear here after Refine phase.";
}

export function CoreShellNode({ data }: NodeProps<CoreShellData>) {
  return (
    <div className="bg-brand-primary text-ink-inverse border-2 border-border-master shadow-brutal-md w-80 p-8 z-20">
      <div className="flex justify-between items-start mb-4">
        <span className="bg-surface-card text-ink-primary px-2 py-0.5 font-mono text-mono-sm uppercase tracking-widest">
          ACTIVE SHELL
        </span>
        <span className="material-symbols-outlined text-ink-inverse" aria-hidden="true">
          hub
        </span>
      </div>

      <h1 className="font-headline text-headline-lg leading-none uppercase mb-4 relative">
        {data.projectName}
      </h1>

      <div className="border-t-2 border-ink-inverse mb-4" />

      <p className="font-body text-body-md mb-6 line-clamp-2">{coreIdeaText(data)}</p>

      <div className="flex gap-2">
        <StatusSquare filled={data.phasesComplete >= 1} />
        <StatusSquare filled={data.phasesComplete >= 2} />
        <StatusSquare filled={data.phasesComplete >= 3} />
      </div>

      <Handle
        type="target"
        position={Position.Top}
        id="core-anchor"
        style={{
          top: 0,
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

function StatusSquare({ filled }: { filled: boolean }) {
  return (
    <div
      className={`h-3 w-3 ${filled ? "bg-ink-inverse" : "border-2 border-ink-inverse"}`}
    />
  );
}
