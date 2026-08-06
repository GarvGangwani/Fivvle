import type { SatelliteNodeId } from "@/lib/types";

/**
 * Canvas phase presentation. Phases are not numbered — the canvas reveals them
 * in order, so position in the journey is shown by what exists, not by a label.
 */
export type ActConfig = {
  actName: string;
  title: string;
  icon: string;
  metricLabel: string;
};

export const ACT_CONFIG: Record<SatelliteNodeId, ActConfig> = {
  spark: {
    actName: "SPARK",
    title: "Capture the raw idea",
    icon: "bolt",
    metricLabel: "Status",
  },
  refine: {
    actName: "REFINE",
    title: "Pressure-test your hypothesis",
    icon: "chat",
    metricLabel: "Messages",
  },
  evidence: {
    actName: "EVIDENCE",
    title: "Market signal from real sources",
    icon: "search",
    metricLabel: "Insights",
  },
  launch: {
    actName: "LAUNCH",
    title: "Landing page + share links",
    icon: "rocket_launch",
    metricLabel: "Views",
  },
  signal: {
    actName: "SIGNAL",
    title: "Metrics + verdict",
    icon: "insights",
    metricLabel: "Demand Score",
  },
  resources: {
    actName: "RESOURCES",
    title: "Notes, links, competitors",
    icon: "folder_open",
    metricLabel: "Items",
  },
};
