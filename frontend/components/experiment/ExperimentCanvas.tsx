"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Controls,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type EdgeTypes,
  type Node,
  type NodeDragHandler,
  type NodeMouseHandler,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";
import { useSearchParams } from "next/navigation";
import { useToast } from "@/components/ui/ToastProvider";
import { createExperimentEvent } from "@/lib/experiment-api";
import type { CanvasNodeId, Experiment } from "@/lib/types";
import { ACT_CONFIG } from "./act-config";
import { BlueprintDecor } from "./BlueprintDecor";
import { CanvasActivityPanel } from "./CanvasActivityPanel";
import { CanvasComposerPill } from "./CanvasComposerPill";
import { CanvasToolbar } from "./CanvasToolbar";
import {
  CORE_NODE_CENTER,
  DEFAULT_CANVAS_ZOOM,
  MIN_CANVAS_ZOOM,
  formatCanvasMetric,
  getPhasesComplete,
  isActRunning,
  snapOutOfExclusionZone,
  snapToGrid,
} from "./canvas-helpers";
import { DeepDiveOverlay } from "./deep-dive/DeepDiveOverlay";
import { ResourcesDrawer } from "./deep-dive/ResourcesDrawer";
import { DashedStraightEdge } from "./edges/DashedStraightEdge";
import { useCanvasLayout } from "./hooks/useCanvasLayout";
import { useResources } from "./hooks/useResources";
import { ActNode } from "./nodes/ActNode";
import { CoreShellNode } from "./nodes/CoreShellNode";

const SATELLITE_IDS: CanvasNodeId[] = [
  "refine",
  "evidence",
  "launch",
  "signal",
  "resources",
];

const nodeTypes: NodeTypes = {
  coreShell: CoreShellNode,
  actNode: ActNode,
};

const edgeTypes: EdgeTypes = {
  "dashed-straight": DashedStraightEdge,
};

const INITIAL_EDGES: Edge[] = SATELLITE_IDS.map((id) => ({
  id: `e-${id}`,
  source: id,
  sourceHandle: "out",
  target: "core",
  targetHandle: "core-anchor",
  type: "dashed-straight",
  selectable: false,
  focusable: false,
}));

const FRAME_CANVAS_DURATION_MS = 200;

type Props = {
  experiment: Experiment;
};

function buildInitialNodes(
  experiment: Experiment,
  positions: Record<CanvasNodeId, { x: number; y: number }>,
  metrics: Record<CanvasNodeId, string>,
  phasesComplete: number,
): Node[] {
  return [
    {
      id: "core",
      type: "coreShell",
      position: { x: 0, y: 0 },
      draggable: false,
      selectable: false,
      data: {
        projectName: experiment.name ?? "UNTITLED PROJECT",
        refinedIdea: experiment.refined_idea ?? null,
        rawIdea: experiment.raw_idea ?? null,
        phasesComplete,
      },
    },
    ...SATELLITE_IDS.map((id) => {
      const config = ACT_CONFIG[id];
      return {
        id,
        type: "actNode",
        position: positions[id],
        data: {
          index: config.index,
          actName: config.actName,
          title: config.title,
          icon: config.icon,
          metricLabel: config.metricLabel,
          metricValue: metrics[id],
          isRunning: isActRunning(id, experiment.status),
        },
      };
    }),
  ];
}

function CanvasInner({ experiment }: Props) {
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const initialAct = searchParams.get("act");
  const [overlayAct, setOverlayAct] = useState<
    "refine" | "evidence" | "launch" | "signal" | null
  >(initialAct === "refine" ? "refine" : null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const { setCenter } = useReactFlow();
  const { positions, loaded, updatePosition, resetLayout } = useCanvasLayout(experiment.id);
  const { resources, addResource, removeResource } = useResources(experiment.id);

  const phasesComplete = getPhasesComplete(experiment.status);
  const resourceCount = Math.max(experiment.resource_count ?? 0, resources.length);

  const metrics = useMemo(
    () => ({
      refine: formatCanvasMetric(experiment.chat_message_count),
      evidence: formatCanvasMetric(experiment.evidence_atom_count),
      launch: formatCanvasMetric(experiment.landing_page_view_count),
      signal:
        experiment.demand_score != null
          ? String(experiment.demand_score)
          : "—",
      resources: formatCanvasMetric(resourceCount),
    }),
    [experiment, resourceCount],
  );

  const initialNodes = useMemo(
    () => buildInitialNodes(experiment, positions, metrics, phasesComplete),
    [experiment, positions, metrics, phasesComplete],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(INITIAL_EDGES);

  useEffect(() => {
    setNodes((current) =>
      current.map((node) => {
        const saved = positions[node.id as CanvasNodeId];
        if (saved && node.id !== "core") {
          return { ...node, position: saved };
        }
        return node;
      }),
    );
  }, [positions, setNodes]);

  useEffect(() => {
    setNodes((current) =>
      current.map((node) => {
        if (node.id === "core") {
          return {
            ...node,
            data: {
              projectName: experiment.name ?? "UNTITLED PROJECT",
              refinedIdea: experiment.refined_idea ?? null,
              rawIdea: experiment.raw_idea ?? null,
              phasesComplete,
            },
          };
        }
        if (!SATELLITE_IDS.includes(node.id as CanvasNodeId)) {
          return node;
        }
        const id = node.id as CanvasNodeId;
        const config = ACT_CONFIG[id];
        return {
          ...node,
          data: {
            index: config.index,
            actName: config.actName,
            title: config.title,
            icon: config.icon,
            metricLabel: config.metricLabel,
            metricValue: metrics[id],
            isRunning: isActRunning(id, experiment.status),
          },
        };
      }),
    );
  }, [experiment, metrics, phasesComplete, setNodes]);

  const frameCanvas = useCallback(() => {
    const zoom = Math.max(MIN_CANVAS_ZOOM, DEFAULT_CANVAS_ZOOM);
    void setCenter(CORE_NODE_CENTER.x, CORE_NODE_CENTER.y, {
      zoom,
      duration: FRAME_CANVAS_DURATION_MS,
    });
  }, [setCenter]);

  useEffect(() => {
    if (!loaded) return;
    frameCanvas();
  }, [loaded, frameCanvas]);

  const onNodeClick: NodeMouseHandler = (_, node) => {
    setFocusedNodeId(node.id);
    if (node.id === "refine") {
      setOverlayAct("refine");
      window.history.pushState({}, "", `?act=refine`);
      return;
    }
    if (node.id === "resources") {
      setResourcesOpen(true);
      return;
    }
    if (node.id !== "core") {
      toast(`${node.id.toUpperCase()} deep-dive coming soon — Step 6.`, "info");
    }
  };

  const closeOverlay = () => {
    setOverlayAct(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("act");
    window.history.pushState({}, "", url.toString());
  };

  const handleFitView = useCallback(() => {
    frameCanvas();
  }, [frameCanvas]);

  const handleResetLayout = useCallback(() => {
    void resetLayout().then(() => {
      frameCanvas();
    });
  }, [resetLayout, frameCanvas]);

  const onNodeDragStop: NodeDragHandler = useCallback(
    (_, node) => {
      if (node.id === "core") return;

      const snapped = snapToGrid(node.position);
      const finalPos = snapOutOfExclusionZone(snapped);

      setNodes((current) =>
        current.map((n) => (n.id === node.id ? { ...n, position: finalPos } : n)),
      );

      updatePosition(node.id as CanvasNodeId, finalPos);
    },
    [setNodes, updatePosition],
  );

  return (
    <div className="relative h-full w-full canvas-grid-bg overflow-hidden">
      <BlueprintDecor />

      <ReactFlow
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        minZoom={0.3}
        maxZoom={2}
        panOnScroll
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{
          type: "dashed-straight",
          style: { stroke: "#777587", strokeWidth: 1.5, strokeDasharray: "6 8" },
        }}
        style={{ background: "transparent" }}
        onNodeClick={onNodeClick}
        onNodeDragStop={onNodeDragStop}
      >
        <Controls
          className="brutalist-controls !left-6 !bottom-24 z-20"
          showInteractive={false}
        />
      </ReactFlow>

      <CanvasToolbar onReset={handleResetLayout} onFitView={handleFitView} />
      <CanvasActivityPanel experimentId={experiment.id} />
      <CanvasComposerPill experimentId={experiment.id} focusedAct={focusedNodeId} />
      <DeepDiveOverlay
        isOpen={overlayAct !== null}
        onClose={closeOverlay}
        act={overlayAct ?? "refine"}
        experimentId={experiment.id}
      />
      <ResourcesDrawer
        open={resourcesOpen}
        resources={resources}
        onClose={() => setResourcesOpen(false)}
        onCreate={async (payload) => {
          await addResource(payload);
          void createExperimentEvent(experiment.id, {
            event_type: "resource_added",
            payload: { title: payload.title },
          });
        }}
        onDelete={async (id) => {
          const resource = resources.find((row) => row.id === id);
          await removeResource(id);
          void createExperimentEvent(experiment.id, {
            event_type: "resource_deleted",
            payload: { title: resource?.title ?? "Resource" },
          });
        }}
      />
    </div>
  );
}

export function ExperimentCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}
