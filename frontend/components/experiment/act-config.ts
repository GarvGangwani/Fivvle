import { Position } from "reactflow";
import type { CanvasNodeId } from "@/lib/types";

export type ActConfig = {
  index: string;
  actName: string;
  title: string;
  icon: string;
  metricLabel: string;
  coreAnchor: string;
  handlePosition: Position;
};

export const ACT_CONFIG: Record<CanvasNodeId, ActConfig> = {
  refine: {
    index: "01",
    actName: "REFINE",
    title: "Pressure-test your hypothesis",
    icon: "chat",
    metricLabel: "Messages",
    coreAnchor: "anchor-right",
    handlePosition: Position.Left,
  },
  evidence: {
    index: "02",
    actName: "EVIDENCE",
    title: "Market signal from real sources",
    icon: "analytics",
    metricLabel: "Insights",
    coreAnchor: "anchor-right",
    handlePosition: Position.Left,
  },
  launch: {
    index: "03",
    actName: "LAUNCH",
    title: "Landing page + share links",
    icon: "rocket_launch",
    metricLabel: "Views",
    coreAnchor: "anchor-left",
    handlePosition: Position.Right,
  },
  signal: {
    index: "04",
    actName: "SIGNAL",
    title: "Metrics + verdict",
    icon: "insights",
    metricLabel: "Demand Score",
    coreAnchor: "anchor-left",
    handlePosition: Position.Right,
  },
  resources: {
    index: "05",
    actName: "RESOURCES",
    title: "Notes, links, competitors",
    icon: "folder_open",
    metricLabel: "Items",
    coreAnchor: "anchor-top",
    handlePosition: Position.Bottom,
  },
};
