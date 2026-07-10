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
  type Viewport,
} from "reactflow";
import "reactflow/dist/style.css";
import { useSearchParams } from "next/navigation";
import { useToast } from "@/components/ui/ToastProvider";
import { getExperiment } from "@/lib/api";
import {
  createExperimentEvent,
  rerunEvidence,
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
  const [evidenceRerunning, setEvidenceRerunning] = useState(false);
  const { setCenter, fitView } = useReactFlow();
  const {
    positions,
    viewport: savedViewport,
    loaded,
    updatePosition,
    updateViewport,
    resetLayout,
  } = useCanvasLayout(experiment.id);
  const [canvasSettled, setCanvasSettled] = useState(false);
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

  // When the panel is open but local position is unset (URL deep-link / popstate),
  // wait until layout has loaded so we read spark-expanded from backend-synced state.
  useEffect(() => {
    if (!sparkPanelOpen || !loaded) return;
    if (sparkPanelPosition !== null) return;
    setSparkPanelPosition(
      positions[SPARK_EXPANDED_ID] ?? computeInitialPanelPosition(),
    );
  }, [
    sparkPanelOpen,
    loaded,
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
    setSparkPanelPosition(null);
    setSparkUrl("closed");
  }, [setSparkUrl]);

  const openSparkPanel = useCallback(() => {
    if (sparkPanelOpen) return;
    // Always prefer backend-synced positions over any leftover local state.
    const savedPos = positions[SPARK_EXPANDED_ID];
    setSparkPanelPosition(savedPos ?? computeInitialPanelPosition());
    setSparkPanelOpen(true);
    setSparkFullscreen(false);
    setSparkUrl("expanded");
  }, [sparkPanelOpen, positions, computeInitialPanelPosition, setSparkUrl]);

  const openSparkFullscreen = useCallback(() => {
    setSparkFullscreen(true);
    setSparkPanelOpen(false);
    setSparkPanelPosition(null);
    setSparkUrl("fullscreen");
  }, [setSparkUrl]);

  const minimizeFromFullscreen = useCallback(() => {
    const savedPos = positions[SPARK_EXPANDED_ID];
    setSparkPanelPosition(savedPos ?? computeInitialPanelPosition());
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
        setSparkPanelPosition(null);
      } else if (act === "spark") {
        setSparkFullscreen(false);
        setSparkPanelPosition(null);
        setSparkPanelOpen(true);
      } else {
        setSparkFullscreen(false);
        setSparkPanelOpen(false);
        setSparkPanelPosition(null);
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleEvidenceRerun = useCallback(async () => {
    setEvidenceRerunning(true);
    try {
      await rerunEvidence(experiment.id);
      toast("Evidence re-run started against the current Spark.", "info");
      const updated = await getExperiment(experiment.id);
      onExperimentChange?.(updated);
    } catch {
      toast("Could not re-run Evidence. Try again.", "error");
    } finally {
      setEvidenceRerunning(false);
    }
  }, [experiment.id, onExperimentChange, toast]);

  const buildNodes = useCallback((): Node[] => {
    const currentSparkVersion = experiment.current_spark_version ?? 0;
    const phaseStale = {
      refine: {
        isStale: Boolean(experiment.refine_is_stale),
        basedOnVersion: experiment.refine_spark_version,
        canRerun: false,
      },
      evidence: {
        isStale: Boolean(experiment.evidence_is_stale),
        basedOnVersion: experiment.evidence_spark_version,
        canRerun: true,
      },
      launch: {
        isStale: Boolean(experiment.launch_is_stale),
        basedOnVersion: experiment.launch_spark_version,
        canRerun: false,
      },
      signal: {
        isStale: Boolean(experiment.signal_is_stale),
        basedOnVersion: experiment.signal_spark_version,
        canRerun: false,
      },
    } as const;

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
          currentSparkVersion,
        },
      },
      ...ACT_NODE_IDS.map((id) => {
        const config = ACT_CONFIG[id];
        const stale =
          id in phaseStale
            ? phaseStale[id as keyof typeof phaseStale]
            : null;
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
            isStale: stale?.isStale ?? false,
            basedOnVersion: stale?.basedOnVersion ?? null,
            currentSparkVersion,
            canRerun: Boolean(stale?.canRerun && stale.isStale),
            rerunning: id === "evidence" ? evidenceRerunning : false,
            onRerun: id === "evidence" ? handleEvidenceRerun : undefined,
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
    evidenceRerunning,
    handleEvidenceRerun,
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

  // Start settle window when ReactFlow mounts (after layout load), not on
  // CanvasInner mount — otherwise a slow GET would leave onMove unguarded.
  useEffect(() => {
    if (!loaded) {
      setCanvasSettled(false);
      return;
    }
    setCanvasSettled(false);
    const timer = window.setTimeout(() => setCanvasSettled(true), 300);
    return () => window.clearTimeout(timer);
  }, [loaded, experiment.id]);

  const handleMove = useCallback(
    (_event: unknown, viewport: Viewport) => {
      if (!canvasSettled) return;
      updateViewport({
        x: viewport.x,
        y: viewport.y,
        zoom: viewport.zoom,
      });
    },
    [canvasSettled, updateViewport],
  );

  const handleFitView = useCallback(() => {
    frameCanvas();
  }, [frameCanvas]);

  const handleResetLayout = useCallback(() => {
    void resetLayout().then(() => {
      requestAnimationFrame(() => {
        fitView({ padding: 0.4, duration: 400 });
      });
    });
  }, [resetLayout, fitView]);

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
      {!loaded ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-mono-md uppercase text-ink-tertiary">
            Loading canvas...
          </span>
        </div>
      ) : (
        <>
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
            defaultViewport={savedViewport ?? undefined}
            fitView={!savedViewport}
            fitViewOptions={{ padding: 0.4 }}
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
            onMove={handleMove}
          >
            <Controls
              className="brutalist-controls !left-6 !bottom-24 z-20"
              showInteractive={false}
            />
          </ReactFlow>
        </>
      )}

      {sparkFullscreen ? (
        <SparkFullscreenModal
          experiment={experiment}
          onClose={closeSparkPanel}
          onMinimize={minimizeFromFullscreen}
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
