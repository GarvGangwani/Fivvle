"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Controls,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type DefaultEdgeOptions,
  type Edge,
  type EdgeTypes,
  type Node,
  type NodeDragHandler,
  type NodeMouseHandler,
  type NodeTypes,
  type ProOptions,
  type Viewport,
} from "reactflow";
import "reactflow/dist/style.css";
import { useSearchParams } from "next/navigation";
import { useToast } from "@/components/ui/ToastProvider";
import { getExperiment, setExperimentTheme } from "@/lib/api";
import {
  createExperimentEvent,
  rerunEvidence,
} from "@/lib/experiment-api";
import {
  DEFAULT_PALETTE_NAME,
  isThemePaletteName,
  paletteAccentOverride,
  type ThemePaletteName,
} from "@/lib/theme-palettes";
import type { CanvasNodeId, Experiment, ExperimentStatus, SatelliteNodeId } from "@/lib/types";
import { ACT_CONFIG } from "./act-config";
import { BlueprintDecor } from "./BlueprintDecor";
import { CanvasToolbar } from "./CanvasToolbar";
import { UniversalChatDock } from "./UniversalChatDock";
import { ThemeConsentDialog } from "./theme/ThemeConsentDialog";
import { ThemePaletteControl } from "./theme/ThemePaletteControl";
import {
  CORE_NODE_CENTER,
  DEFAULT_CANVAS_ZOOM,
  DEFAULT_POSITIONS,
  MIN_CANVAS_ZOOM,
  experimentHasOriginalIdea,
  formatCanvasMetric,
  getNodeLockState,
  getPhasesComplete,
  isActRunning,
  snapOutOfExclusionZone,
  snapToGrid,
} from "./canvas-helpers";
import { originAttachmentsForArtifact } from "./idea-capture-helpers";
import {
  applyRouteAccent,
  canvasAccentCssVars,
  type CanvasAccentOverride,
} from "./canvas-accent";
import {
  DeepDiveOverlay,
  type DeepDiveAct,
} from "./deep-dive/DeepDiveOverlay";
import { ResourcesDrawer } from "./deep-dive/ResourcesDrawer";
import { DashedCurvedEdge } from "./edges/DashedCurvedEdge";
import { useCanvasLayout } from "./hooks/useCanvasLayout";
import { useResources } from "./hooks/useResources";
import { ActNode } from "./nodes/ActNode";
import { CoreShellNode } from "./nodes/CoreShellNode";
import { OriginArtifactNode } from "./nodes/OriginArtifactNode";
import { OriginDormantNode } from "./nodes/OriginDormantNode";
import { useRefineChat } from "./refine/useRefineChat";

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

const nodeTypes: NodeTypes = {
  coreShell: CoreShellNode,
  actNode: ActNode,
  originArtifact: OriginArtifactNode,
  originDormant: OriginDormantNode,
};

const edgeTypes: EdgeTypes = {
  "dashed-straight": DashedCurvedEdge,
};

/** Stable across renders — CSS vars resolve at paint time, no theme JS dependency. */
const DEFAULT_EDGE_OPTIONS: DefaultEdgeOptions = {
  type: "dashed-straight",
  style: {
    stroke: "var(--fv-canvas-edge)",
    strokeWidth: 1.5,
    strokeDasharray: "6 8",
  },
};

const PRO_OPTIONS: ProOptions = { hideAttribution: true };

const FIT_VIEW_OPTIONS = { padding: 0.4 };

const REACT_FLOW_STYLE = { background: "transparent" } as const;

const CONTROLS_STYLE = { left: 24, bottom: 64, margin: 0 };

function buildSatelliteEdges(experiment: Experiment): Edge[] {
  return SATELLITE_IDS.map((id) => ({
    id: `e-${id}`,
    source: id,
    sourceHandle: "out",
    target: "core",
    targetHandle: "core-anchor",
    type: "dashed-straight",
    selectable: false,
    focusable: false,
    data: { isLocked: getNodeLockState(id, experiment).isLocked },
  }));
}

const FRAME_CANVAS_DURATION_MS = 200;

type Props = {
  experiment: Experiment;
  onExperimentChange?: (experiment: Experiment) => void;
  /**
   * Escape hatch that wins over the experiment's palette. Only affects this
   * wrapper — FloatingAppNav / dashboard sit outside it and stay platform purple.
   */
  accentOverride?: CanvasAccentOverride | string | null;
};

function CanvasInner({
  experiment,
  onExperimentChange,
  accentOverride,
}: Props) {
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const initialAct = searchParams.get("act");

  const [overlayAct, setOverlayAct] = useState<DeepDiveAct | null>(() => {
    // Legacy ?act=spark deep-links are ignored — capture lives in chat.
    if (
      initialAct === "refine" ||
      initialAct === "evidence" ||
      initialAct === "launch" ||
      initialAct === "signal"
    ) {
      return initialAct;
    }
    return null;
  });
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const [evidenceRerunning, setEvidenceRerunning] = useState(false);
  const [chatDockCollapsed, setChatDockCollapsed] = useState(false);
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
  /** Live viewport during pan/zoom — ref only, never triggers re-render. */
  const viewportRef = useRef<Viewport | null>(null);
  const { resources, addResource, removeResource } = useResources(experiment.id);

  // Seed ref from hydrated layout (initial load / experiment switch).
  useEffect(() => {
    viewportRef.current = savedViewport;
  }, [savedViewport]);

  const refineSurfaceOpen = overlayAct === "refine";
  const enableOpener =
    refineSurfaceOpen &&
    experimentHasOriginalIdea(experiment) &&
    Boolean(experiment.raw_idea?.trim());

  const onExperimentRefresh = useCallback(async () => {
    if (!onExperimentChange) return;
    const updated = await getExperiment(experiment.id);
    onExperimentChange(updated);
  }, [experiment.id, onExperimentChange]);

  /** Held locally so a palette switch recolors before the PATCH round-trips. */
  const [activePalette, setActivePalette] = useState<string | null>(
    experiment.theme_palette ?? null,
  );
  useEffect(() => {
    setActivePalette(experiment.theme_palette ?? null);
  }, [experiment.theme_palette]);

  const [paletteConsent, setPaletteConsent] = useState<{
    palette: string;
    resolve: () => void;
  } | null>(null);
  const [paletteBusy, setPaletteBusy] = useState(false);

  const applyPalette = useCallback(
    async (next: ThemePaletteName | null) => {
      const previous = activePalette;
      setActivePalette(next);
      try {
        const updated = await setExperimentTheme(experiment.id, next);
        onExperimentChange?.(updated);
      } catch {
        setActivePalette(previous);
        toast("Could not save the canvas theme. Try again.", "error");
      }
    },
    [activePalette, experiment.id, onExperimentChange, toast],
  );

  /**
   * Resolves once the founder answers, so the dock can await consent before
   * handing the canvas to refine. Default suggestions need no prompt.
   */
  const requestPaletteConsent = useCallback(
    (paletteName: string) =>
      new Promise<void>((resolve) => {
        if (
          !isThemePaletteName(paletteName) ||
          paletteName === DEFAULT_PALETTE_NAME
        ) {
          resolve();
          return;
        }
        setPaletteConsent({ palette: paletteName, resolve });
      }),
    [],
  );

  const closePaletteConsent = useCallback(() => {
    paletteConsent?.resolve();
    setPaletteConsent(null);
    setPaletteBusy(false);
  }, [paletteConsent]);

  const acceptSuggestedPalette = useCallback(async () => {
    if (!paletteConsent) return;
    setPaletteBusy(true);
    if (isThemePaletteName(paletteConsent.palette)) {
      await applyPalette(paletteConsent.palette);
    }
    closePaletteConsent();
  }, [applyPalette, closePaletteConsent, paletteConsent]);

  const {
    messages: refineMessages,
    reload: reloadRefineChat,
  } = useRefineChat(experiment.id, {
    onTurnComplete: onExperimentRefresh,
    enableOpener,
  });

  const refreshExperimentAndChat = useCallback(async () => {
    const updated = await getExperiment(experiment.id);
    onExperimentChange?.(updated);
    reloadRefineChat();
  }, [experiment.id, onExperimentChange, reloadRefineChat]);

  const phasesComplete = getPhasesComplete(experiment.status);
  const resourceCount = Math.max(experiment.resource_count ?? 0, resources.length);

  const metrics = useMemo(
    () =>
      ({
        spark: experimentHasOriginalIdea(experiment) ? "SEALED" : "—",
        refine: formatCanvasMetric(experiment.chat_message_count),
        evidence: formatCanvasMetric(experiment.evidence_atom_count),
        launch: formatCanvasMetric(experiment.landing_page_view_count),
        signal:
          experiment.demand_score != null
            ? String(experiment.demand_score)
            : "—",
        resources: formatCanvasMetric(resourceCount),
      }) satisfies Record<SatelliteNodeId, string>,
    [experiment, resourceCount],
  );

  const setOverlayUrl = useCallback((act: DeepDiveAct | null) => {
    const url = new URL(window.location.href);
    url.searchParams.delete("view");
    if (act) {
      url.searchParams.set("act", act);
    } else {
      url.searchParams.delete("act");
    }
    window.history.pushState({}, "", url.toString());
  }, []);

  const openPhaseOverlay = useCallback(
    (
      act: DeepDiveAct,
      _options?: { sourceRef?: { source_url?: string | null } | null },
    ) => {
      if (act === "refine") {
        const lockState = getNodeLockState("refine", experiment);
        if (lockState.isLocked) {
          toast(
            lockState.unlockRequirement ??
              "Capture your original idea in chat to unlock Refine.",
            "info",
          );
          return;
        }
      }
      setOverlayAct(act);
      setOverlayUrl(act);
    },
    [experiment, setOverlayUrl, toast],
  );

  useEffect(() => {
    const onPopState = () => {
      const params = new URLSearchParams(window.location.search);
      const act = params.get("act");
      if (
        act === "evidence" ||
        act === "launch" ||
        act === "signal" ||
        act === "refine"
      ) {
        setOverlayAct(act);
      } else {
        setOverlayAct(null);
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleEvidenceRerun = useCallback(async () => {
    setEvidenceRerunning(true);
    try {
      await rerunEvidence(experiment.id);
      toast("Evidence re-run started against the current origin.", "info");
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

    const hasOrigin = experimentHasOriginalIdea(experiment);

    return [
      {
        id: "core",
        type: "coreShell",
        position: { x: 0, y: 0 },
        draggable: false,
        selectable: false,
        data: {
          projectName: experiment.name ?? "UNTITLED PROJECT",
          refinedIdea:
            typeof experiment.refined_idea === "string"
              ? experiment.refined_idea
              : experiment.refined_idea?.refined_one_liner ?? null,
          rawIdea: experiment.raw_idea ?? null,
          phasesComplete,
        },
      },
      {
        id: "spark",
        type: hasOrigin
          ? ("originArtifact" as const)
          : ("originDormant" as const),
        position: positions.spark ?? DEFAULT_POSITIONS.spark,
        data: hasOrigin
          ? {
              originalIdea: experiment.original_idea ?? "",
              capturedAt: experiment.original_idea_captured_at ?? null,
              attachments: originAttachmentsForArtifact(
                experiment.id,
                experiment.origin_attachments,
              ),
            }
          : {
              projectName: experiment.name ?? null,
            },
      },
      ...ACT_NODE_IDS.map((id) => {
        const config = ACT_CONFIG[id];
        const stale =
          id in phaseStale
            ? phaseStale[id as keyof typeof phaseStale]
            : null;
        const lockState = getNodeLockState(id, experiment);
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
            isFocused: overlayAct === id,
            isLocked: lockState.isLocked,
            unlockRequirement: lockState.unlockRequirement,
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
  }, [
    experiment,
    phasesComplete,
    positions,
    overlayAct,
    metrics,
    evidenceRerunning,
    handleEvidenceRerun,
  ]);

  const [nodes, setNodes, onNodesChange] = useNodesState(buildNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    buildSatelliteEdges(experiment),
  );

  useEffect(() => {
    setNodes((current) => {
      const next = buildNodes();
      if (current.length === 0) return next;
      const currentById = new Map(current.map((n) => [n.id, n]));
      return next.map((n) => {
        const prev = currentById.get(n.id);
        if (!prev) return n;
        // While dragging, never clobber the live RF position with a rebuild
        // (buildNodes reads layout state, which only updates on drag-stop).
        if (prev.dragging) {
          return {
            ...n,
            position: prev.position,
            dragging: true,
            selected: prev.selected,
          };
        }
        return {
          ...n,
          selected: prev.selected,
        };
      });
    });
  }, [buildNodes, setNodes]);

  useEffect(() => {
    setEdges(buildSatelliteEdges(experiment));
  }, [experiment, setEdges]);

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
      viewportRef.current = {
        x: viewport.x,
        y: viewport.y,
        zoom: viewport.zoom,
      };
    },
    [canvasSettled],
  );

  const handleMoveEnd = useCallback(
    (_event: unknown, viewport: Viewport) => {
      if (!canvasSettled) return;
      const next = {
        x: viewport.x,
        y: viewport.y,
        zoom: viewport.zoom,
      };
      viewportRef.current = next;
      updateViewport(next);
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
    const lockState = getNodeLockState(node.id, experiment);
    if (lockState.isLocked) {
      toast(
        lockState.unlockRequirement ?? "This phase isn't unlocked yet.",
        "info",
      );
      return;
    }

    if (node.id === "spark") {
      // Origin slot is read-only (artifact) or dormant (capture in chat).
      return;
    }
    if (node.id === "refine") {
      openPhaseOverlay("refine");
      return;
    }
    if (node.id === "resources") {
      setResourcesOpen(true);
      return;
    }
    if (node.id === "evidence") {
      openPhaseOverlay("evidence");
      return;
    }
    if (node.id === "launch") {
      openPhaseOverlay("launch");
      return;
    }
    if (node.id === "signal") {
      openPhaseOverlay("signal");
      return;
    }
    if (node.id !== "core") {
      toast(`${node.id.toUpperCase()} deep-dive coming soon — Step 6.`, "info");
    }
  };

  const closeOverlay = () => {
    setOverlayAct(null);
    setOverlayUrl(null);
  };

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

  const resolvedAccent = useMemo(
    () => accentOverride ?? paletteAccentOverride(activePalette),
    [accentOverride, activePalette],
  );

  const accentStyle = useMemo(
    () => canvasAccentCssVars(resolvedAccent),
    [resolvedAccent],
  );

  // Themes the canvas-route side rail, which renders above this wrapper.
  useEffect(() => applyRouteAccent(resolvedAccent), [resolvedAccent]);

  return (
    <div
      className="relative h-full w-full canvas-grid-bg overflow-hidden"
      data-canvas-accent-scope=""
      style={accentStyle}
    >
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
            proOptions={PRO_OPTIONS}
            defaultViewport={savedViewport ?? undefined}
            fitView={!savedViewport}
            fitViewOptions={FIT_VIEW_OPTIONS}
            defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
            style={REACT_FLOW_STYLE}
            onNodeClick={onNodeClick}
            onNodeDragStop={onNodeDragStop}
            onMove={handleMove}
            onMoveEnd={handleMoveEnd}
            // Avoid selection/focus work while dragging satellites.
            selectNodesOnDrag={false}
            nodesFocusable={false}
            edgesFocusable={false}
          >
            <Controls
              className="brutalist-controls"
              showInteractive={false}
              style={CONTROLS_STYLE}
            />
          </ReactFlow>
        </>
      )}

      <CanvasToolbar onReset={handleResetLayout} onFitView={handleFitView} />
      <ThemePaletteControl
        active={activePalette}
        suggested={experiment.suggested_palette ?? null}
        onSelect={(palette) => void applyPalette(palette)}
      />
      {paletteConsent ? (
        <ThemeConsentDialog
          projectName={experiment.name ?? null}
          paletteName={paletteConsent.palette}
          busy={paletteBusy}
          onAccept={() => void acceptSuggestedPalette()}
          onDecline={closePaletteConsent}
        />
      ) : null}
      <UniversalChatDock
        experimentId={experiment.id}
        projectName={experiment.name}
        onCollapsedChange={setChatDockCollapsed}
        currentOpenPhase={overlayAct}
        onOpenPhase={openPhaseOverlay}
        needsIdeaCapture={!experimentHasOriginalIdea(experiment)}
        onIdeaCaptured={onExperimentRefresh}
        onPaletteSuggested={requestPaletteConsent}
      />
      <DeepDiveOverlay
        isOpen={overlayAct !== null}
        onClose={closeOverlay}
        act={overlayAct ?? "evidence"}
        experimentId={experiment.id}
        experiment={experiment}
        experimentStatus={experiment.status as ExperimentStatus}
        projectName={experiment.name?.trim() || "Untitled project"}
        founderDecision={experiment.founder_decision ?? null}
        founderDecisionAt={experiment.founder_decision_at ?? null}
        founderDecisionNote={experiment.founder_decision_note ?? null}
        founderDecisionVersion={experiment.founder_decision_version ?? null}
        onExperimentRefresh={onExperimentRefresh}
        onExperimentChange={onExperimentChange}
        onOpenLaunch={() => openPhaseOverlay("launch")}
        chatDockCollapsed={chatDockCollapsed}
        refinePanel={
          overlayAct === "refine"
            ? {
                messages: refineMessages,
                onFinalizedOrReset: refreshExperimentAndChat,
              }
            : null
        }
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
