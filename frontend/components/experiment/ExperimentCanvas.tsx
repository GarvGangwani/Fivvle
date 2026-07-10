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
import {
  createExperimentEvent,
  patchExperimentSpark,
} from "@/lib/experiment-api";
import type { CanvasNodeId, Experiment, SatelliteNodeId } from "@/lib/types";
import { ACT_CONFIG } from "./act-config";
import { BlueprintDecor } from "./BlueprintDecor";
import { CanvasActivityPanel } from "./CanvasActivityPanel";
import { CanvasComposerPill } from "./CanvasComposerPill";
import { CanvasToolbar } from "./CanvasToolbar";
import {
  CORE_NODE_CENTER,
  DEFAULT_CANVAS_ZOOM,
  DEFAULT_POSITIONS,
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
import { SparkExpandedNode } from "./nodes/SparkExpandedNode";
import { SparkFullscreenModal } from "./nodes/SparkFullscreenModal";
import { SparkNode, type SparkMetricState } from "./nodes/SparkNode";

const SATELLITE_IDS: SatelliteNodeId[] = [
  "spark",
  "refine",
  "evidence",
  "launch",
  "signal",
  "resources",
];

const ACT_NODE_IDS: SatelliteNodeId[] = [
  "refine",
  "evidence",
  "launch",
  "signal",
  "resources",
];

const SPARK_EXPANDED_ID = "spark-expanded" as const;

const nodeTypes: NodeTypes = {
  coreShell: CoreShellNode,
  actNode: ActNode,
  sparkNode: SparkNode,
  sparkExpanded: SparkExpandedNode,
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
  onExperimentChange?: (experiment: Experiment) => void;
};

function getSparkMetric(experiment: Experiment): {
  value: string;
  state: SparkMetricState;
} {
  const hasIdea = Boolean(experiment.raw_idea?.trim());
  const attachmentCount = experiment.attachment_count ?? 0;
  const refinementStarted = Boolean(experiment.refinement_started_at);

  if (!hasIdea && attachmentCount === 0) {
    return { value: "NEEDS INPUT", state: "empty" };
  }
  if (refinementStarted) {
    const parts = ["IDEA CAPTURED"];
    if (attachmentCount > 0) parts.push(`${attachmentCount} FILES`);
    return { value: parts.join(" · "), state: "locked" };
  }
  const parts = ["IDEA DRAFTED"];
  if (attachmentCount > 0) parts.push(`${attachmentCount} FILES`);
  return { value: parts.join(" · "), state: "drafted" };
}

function CanvasInner({ experiment, onExperimentChange }: Props) {
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const initialAct = searchParams.get("act");
  const initialView = searchParams.get("view");

  const [overlayAct, setOverlayAct] = useState<
    "refine" | "evidence" | "launch" | "signal" | null
  >(initialAct === "refine" ? "refine" : null);
  const [sparkPanelOpen, setSparkPanelOpen] = useState(
    () => initialAct === "spark" && initialView !== "fullscreen",
  );
  const [sparkFullscreen, setSparkFullscreen] = useState(
    () => initialAct === "spark" && initialView === "fullscreen",
  );
  const [sparkPanelPosition, setSparkPanelPosition] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const { setCenter } = useReactFlow();
  const { positions, loaded, updatePosition, resetLayout } = useCanvasLayout(
    experiment.id,
  );
  const { resources, addResource, removeResource } = useResources(experiment.id);

  const phasesComplete = getPhasesComplete(experiment.status);
  const resourceCount = Math.max(experiment.resource_count ?? 0, resources.length);
  const sparkMetric = useMemo(() => getSparkMetric(experiment), [experiment]);

  const metrics = useMemo(
    () =>
      ({
        spark: sparkMetric.value,
        refine: formatCanvasMetric(experiment.chat_message_count),
        evidence: formatCanvasMetric(experiment.evidence_atom_count),
        launch: formatCanvasMetric(experiment.landing_page_view_count),
        signal:
          experiment.demand_score != null
            ? String(experiment.demand_score)
            : "—",
        resources: formatCanvasMetric(resourceCount),
      }) satisfies Record<SatelliteNodeId, string>,
    [experiment, resourceCount, sparkMetric.value],
  );

  const computeInitialPanelPosition = useCallback(() => {
    const sparkPos = positions.spark ?? DEFAULT_POSITIONS.spark;
    return { x: sparkPos.x + 340, y: sparkPos.y };
  }, [positions]);

  useEffect(() => {
    if (!sparkPanelOpen) return;
    if (sparkPanelPosition) return;
    const saved = positions[SPARK_EXPANDED_ID];
    setSparkPanelPosition(saved ?? computeInitialPanelPosition());
  }, [
    sparkPanelOpen,
    sparkPanelPosition,
    positions,
    computeInitialPanelPosition,
  ]);

  const setSparkUrl = useCallback(
    (state: "closed" | "expanded" | "fullscreen") => {
      const url = new URL(window.location.href);
      if (state === "closed") {
        url.searchParams.delete("act");
        url.searchParams.delete("view");
      } else {
        url.searchParams.set("act", "spark");
        url.searchParams.set("view", state);
      }
      window.history.pushState({}, "", url.toString());
    },
    [],
  );

  const closeSparkPanel = useCallback(() => {
    setSparkPanelOpen(false);
    setSparkFullscreen(false);
    setSparkUrl("closed");
  }, [setSparkUrl]);

  const openSparkPanel = useCallback(() => {
    const saved = positions[SPARK_EXPANDED_ID];
    setSparkPanelPosition(saved ?? computeInitialPanelPosition());
    setSparkPanelOpen(true);
    setSparkFullscreen(false);
    setSparkUrl("expanded");
  }, [positions, computeInitialPanelPosition, setSparkUrl]);

  const openSparkFullscreen = useCallback(() => {
    setSparkFullscreen(true);
    setSparkPanelOpen(false);
    setSparkUrl("fullscreen");
  }, [setSparkUrl]);

  const minimizeFromFullscreen = useCallback(() => {
    const saved = positions[SPARK_EXPANDED_ID];
    setSparkPanelPosition(saved ?? computeInitialPanelPosition());
    setSparkFullscreen(false);
    setSparkPanelOpen(true);
    setSparkUrl("expanded");
  }, [positions, computeInitialPanelPosition, setSparkUrl]);

  useEffect(() => {
    const onPopState = () => {
      const params = new URLSearchParams(window.location.search);
      const act = params.get("act");
      const view = params.get("view");
      setOverlayAct(act === "refine" ? "refine" : null);
      if (act === "spark" && view === "fullscreen") {
        setSparkFullscreen(true);
        setSparkPanelOpen(false);
      } else if (act === "spark") {
        setSparkFullscreen(false);
        setSparkPanelOpen(true);
      } else {
        setSparkFullscreen(false);
        setSparkPanelOpen(false);
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const buildNodes = useCallback((): Node[] => {
    const base: Node[] = [
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
      {
        id: "spark",
        type: "sparkNode",
        position: positions.spark ?? DEFAULT_POSITIONS.spark,
        data: {
          rawIdea: experiment.raw_idea ?? null,
          sparkMetric,
          isFocused: sparkPanelOpen || sparkFullscreen,
          isRunning: isActRunning("spark", experiment.status),
        },
      },
      ...ACT_NODE_IDS.map((id) => {
        const config = ACT_CONFIG[id];
        return {
          id,
          type: "actNode" as const,
          position: positions[id] ?? DEFAULT_POSITIONS[id],
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

    if (sparkPanelOpen && sparkPanelPosition) {
      base.push({
        id: SPARK_EXPANDED_ID,
        type: "sparkExpanded",
        position: sparkPanelPosition,
        draggable: true,
        selectable: true,
        data: {
          experiment,
          onClose: closeSparkPanel,
          onFullscreen: openSparkFullscreen,
          onSave: async (rawIdea: string) => {
            const updated = await patchExperimentSpark(experiment.id, rawIdea);
            onExperimentChange?.(updated);
          },
          onExperimentChange,
        },
      });
    }

    return base;
  }, [
    experiment,
    phasesComplete,
    positions,
    sparkMetric,
    sparkPanelOpen,
    sparkFullscreen,
    sparkPanelPosition,
    metrics,
    closeSparkPanel,
    openSparkFullscreen,
    onExperimentChange,
  ]);

  const [nodes, setNodes, onNodesChange] = useNodesState(buildNodes());
  const [edges, , onEdgesChange] = useEdgesState(INITIAL_EDGES);

  useEffect(() => {
    setNodes(buildNodes());
  }, [buildNodes, setNodes]);

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
    if (node.id === SPARK_EXPANDED_ID) return;
    setFocusedNodeId(node.id);
    if (node.id === "spark") {
      openSparkPanel();
      return;
    }
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
      const finalPos =
        node.id === SPARK_EXPANDED_ID
          ? snapped
          : snapOutOfExclusionZone(snapped);

      setNodes((current) =>
        current.map((n) => (n.id === node.id ? { ...n, position: finalPos } : n)),
      );

      updatePosition(node.id as CanvasNodeId, finalPos);

      if (node.id === SPARK_EXPANDED_ID) {
        setSparkPanelPosition(finalPos);
      }
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
          style: {
            stroke: "#777587",
            strokeWidth: 1.5,
            strokeDasharray: "6 8",
          },
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

      {sparkFullscreen ? (
        <SparkFullscreenModal
          experiment={experiment}
          onClose={closeSparkPanel}
          onMinimize={minimizeFromFullscreen}
          onSave={async (rawIdea) => {
            const updated = await patchExperimentSpark(experiment.id, rawIdea);
            onExperimentChange?.(updated);
          }}
          onExperimentChange={onExperimentChange}
        />
      ) : null}

      <CanvasToolbar onReset={handleResetLayout} onFitView={handleFitView} />
      <CanvasActivityPanel experimentId={experiment.id} />
      <CanvasComposerPill
        experimentId={experiment.id}
        focusedAct={focusedNodeId}
      />
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
