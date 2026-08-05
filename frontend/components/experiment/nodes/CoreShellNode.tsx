"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

type CoreShellData = {
  projectName: string;
  refinedIdea: string | null;
  rawIdea: string | null;
  phasesComplete: number;
};

function CoreShellNodeComponent({ data }: NodeProps<CoreShellData>) {
  return (
    <div className="z-20 w-80 rounded-md border-2 border-border-master bg-accent p-8 text-ink-inverse shadow-brutal-md fv-brutal-hover-glow">
      <div className="mb-4 flex items-start justify-between">
        <span className="bg-surface-card px-2 py-0.5 font-mono text-mono-sm uppercase tracking-widest text-ink-primary">
          ACTIVE SHELL
        </span>
        <span className="material-symbols-outlined text-ink-inverse" aria-hidden="true">
          hub
        </span>
      </div>

      <h1 className="relative mb-4 font-headline text-headline-lg uppercase leading-none">
        {data.projectName}
      </h1>

      <div className="mb-4 border-t-2 border-ink-inverse" />

      {data.refinedIdea ? (
        <p className="mb-6 line-clamp-2 font-body text-body-md">
          {data.refinedIdea}
        </p>
      ) : data.rawIdea?.trim() ? (
        <p className="mb-6 line-clamp-2 font-body text-body-md">
          {data.rawIdea.trim().length > 120
            ? `${data.rawIdea.trim().slice(0, 120)}...`
            : data.rawIdea.trim()}
        </p>
      ) : (
        <p className="mb-6 font-body text-body-md italic opacity-60">
          Add your idea in the Spark phase to get started.
        </p>
      )}

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

export const CoreShellNode = memo(CoreShellNodeComponent);
