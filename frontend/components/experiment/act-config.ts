import type { SatelliteNodeId } from "@/lib/types";

export type ActConfig = {
  index: string;
  actName: string;
  title: string;
  icon: string;
  metricLabel: string;
};

export const ACT_CONFIG: Record<SatelliteNodeId, ActConfig> = {
  spark: {
    index: "01",
    actName: "SPARK",
    title: "Capture the raw idea",
    icon: "bolt",
    metricLabel: "Status",
  },
  refine: {
    index: "02",
    actName: "REFINE",
    title: "Pressure-test your hypothesis",
    icon: "chat",
    metricLabel: "Messages",
  },
  evidence: {
    index: "03",
    actName: "EVIDENCE",
    title: "Market signal from real sources",
    icon: "search",
    metricLabel: "Insights",
  },
  launch: {
    index: "04",
    actName: "LAUNCH",
    title: "Landing page + share links",
    icon: "rocket_launch",
    metricLabel: "Views",
  },
  signal: {
    index: "05",
    actName: "SIGNAL",
    title: "Metrics + verdict",
    icon: "insights",
    metricLabel: "Demand Score",
  },
  resources: {
    index: "06",
    actName: "RESOURCES",
    title: "Notes, links, competitors",
    icon: "folder_open",
    metricLabel: "Items",
  },
};
