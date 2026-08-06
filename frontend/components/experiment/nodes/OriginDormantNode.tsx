"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

const INVISIBLE_HANDLE = {
  background: "transparent",
  border: "none",
  width: 1,
  height: 1,
  pointerEvents: "none" as const,
};

export type OriginDormantNodeData = {
  projectName?: string | null;
};

/** Pre-capture spark-slot placeholder — idea capture lives in the chat rail. */
function OriginDormantNodeComponent({ data }: NodeProps<OriginDormantNodeData>) {
  const name = data.projectName?.trim();

  return (
    <div className="w-64 rounded-md border-2 border-dashed border-border-master bg-surface-card/80 p-4 opacity-90">
      <div className="mb-3 flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-ink-tertiary" />
        <span className="font-label-md text-label-md font-black uppercase text-ink-tertiary">
          ORIGIN
        </span>
      </div>

      <h3 className="mb-3 border-b-2 border-ink-primary/10 pb-3 font-headline text-headline-md text-ink-secondary">
        {name ? `Awaiting ${name}` : "Awaiting capture"}
      </h3>

      {/* No LOCKED chip — phases are revealed progressively, so nothing on the
          canvas is presented as locked. */}
      <p className="font-body text-body-sm text-ink-tertiary">
        Describe your idea in chat to seal the original.
      </p>

      <Handle
        type="source"
        position={Position.Bottom}
        id="out"
        style={INVISIBLE_HANDLE}
      />
    </div>
  );
}

export const OriginDormantNode = memo(OriginDormantNodeComponent);
