"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import type { ExperimentAttachment } from "@/lib/types";
import { OriginProvenanceCard } from "@/components/experiment/origin-artifact/OriginProvenanceCard";
import {
  formatCaptureDateTime,
  originVersionLabel,
} from "@/components/experiment/origin-artifact/origin-artifact-utils";

/** Matches OriginProvenanceCard canvas width. */
const CARD_WIDTH = 392;

const INVISIBLE_HANDLE = {
  background: "transparent",
  border: "none",
  width: 1,
  height: 1,
  pointerEvents: "none" as const,
};

export type OriginArtifactNodeData = {
  originalIdea: string;
  capturedAt: string | null;
  attachments: ExperimentAttachment[];
};

function OriginArtifactNodeComponent({
  data,
}: NodeProps<OriginArtifactNodeData>) {
  return (
    <div className="relative" style={{ width: CARD_WIDTH }}>
      <OriginProvenanceCard
        rawIdea={data.originalIdea}
        captureDate={formatCaptureDateTime(data.capturedAt)}
        versionTag={originVersionLabel()}
        attachments={data.attachments}
      />

      <Handle
        type="target"
        position={Position.Top}
        id="in"
        style={INVISIBLE_HANDLE}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="out"
        style={INVISIBLE_HANDLE}
      />
    </div>
  );
}

export const OriginArtifactNode = memo(OriginArtifactNodeComponent);
