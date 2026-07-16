"use client";

import { useMemo } from "react";
import { type EdgeProps, type ReactFlowState, useStore } from "reactflow";

type NodeBox = { x: number; y: number; width: number; height: number };

function intersectionOnBox(box: NodeBox, target: { x: number; y: number }) {
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  const dx = target.x - cx;
  const dy = target.y - cy;

  if (dx === 0 && dy === 0) return { x: cx, y: cy };

  const hw = box.width / 2;
  const hh = box.height / 2;

  const scaleX = hw / Math.abs(dx || 1);
  const scaleY = hh / Math.abs(dy || 1);
  const scale = Math.min(scaleX, scaleY);

  return { x: cx + dx * scale, y: cy + dy * scale };
}

function getNodeBox(
  node: NonNullable<ReturnType<ReactFlowState["nodeInternals"]["get"]>>,
): NodeBox {
  return {
    x: node.positionAbsolute?.x ?? node.position.x,
    y: node.positionAbsolute?.y ?? node.position.y,
    width: node.width ?? 0,
    height: node.height ?? 0,
  };
}

function boxesEqual(a: NodeBox | null, b: NodeBox | null): boolean {
  if (!a || !b) return a === b;
  return (
    a.x === b.x &&
    a.y === b.y &&
    a.width === b.width &&
    a.height === b.height
  );
}

export function DashedStraightEdge({ id, source, target, style }: EdgeProps) {
  const { sourceBox, targetBox } = useStore(
    (s: ReactFlowState) => {
      const sourceNode = s.nodeInternals.get(source);
      const targetNode = s.nodeInternals.get(target);

      if (!sourceNode || !targetNode) {
        return { sourceBox: null, targetBox: null };
      }

      return {
        sourceBox: getNodeBox(sourceNode),
        targetBox: getNodeBox(targetNode),
      };
    },
    (a, b) => {
      if (!a.sourceBox || !b.sourceBox || !a.targetBox || !b.targetBox) {
        return a.sourceBox === b.sourceBox && a.targetBox === b.targetBox;
      }
      return (
        boxesEqual(a.sourceBox, b.sourceBox) &&
        boxesEqual(a.targetBox, b.targetBox)
      );
    },
  );

  const { startPoint, endPoint } = useMemo(() => {
    if (!sourceBox || !targetBox) return { startPoint: null, endPoint: null };
    if (!sourceBox.width || !sourceBox.height) {
      return { startPoint: null, endPoint: null };
    }
    if (!targetBox.width || !targetBox.height) {
      return { startPoint: null, endPoint: null };
    }

    const sourceCenter = {
      x: sourceBox.x + sourceBox.width / 2,
      y: sourceBox.y + sourceBox.height / 2,
    };
    const targetCenter = {
      x: targetBox.x + targetBox.width / 2,
      y: targetBox.y + targetBox.height / 2,
    };

    return {
      startPoint: intersectionOnBox(sourceBox, targetCenter),
      endPoint: intersectionOnBox(targetBox, sourceCenter),
    };
  }, [sourceBox, targetBox]);

  if (!startPoint || !endPoint) return null;

  const path = `M ${startPoint.x},${startPoint.y} L ${endPoint.x},${endPoint.y}`;

  return (
    <g className="react-flow__edge-path" style={{ zIndex: 0 }}>
      <path
        id={id}
        d={path}
        fill="none"
        strokeWidth={1.5}
        stroke="var(--fv-canvas-edge)"
        strokeDasharray="6 8"
        style={style}
      />
      <circle cx={startPoint.x} cy={startPoint.y} r={3.5} fill="var(--fv-canvas-edge)" />
      <circle cx={endPoint.x} cy={endPoint.y} r={3.5} fill="var(--fv-canvas-edge)" />
    </g>
  );
}
