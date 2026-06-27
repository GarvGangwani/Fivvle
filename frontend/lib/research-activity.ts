/** Activity copy for the inline research progress feed (Gemini Deep Research style). */

import { RESEARCH_PHASE_LABELS } from "@/components/research/PhaseIndicator";

const PHASE_ACTIVITY: Record<string, readonly string[]> = {
  RESEARCHING: [
    "Starting the research pipeline…",
    "Loading your refined hypothesis…",
    "Preparing planner and source integrations…",
  ],
  RESEARCH_PLANNING: [
    "Breaking your idea into research questions…",
    "Identifying competitors and market angles…",
    "Prioritizing Tavily, Reddit, and Trends queries…",
    "Mapping evidence targets for each claim…",
  ],
  RESEARCH_SEARCHING: [
    "Searching the web for competitor landscape…",
    "Querying Reddit for real user pain points…",
    "Checking Google Trends for demand signals…",
    "Collecting news and industry sources…",
    "Gathering citations for market validation…",
  ],
  RESEARCH_READING: [
    "Extracting key quotes from top sources…",
    "Reading competitor positioning pages…",
    "Pulling specific complaints from forums…",
    "Scoring source reliability…",
    "Building evidence cards per finding…",
  ],
  RESEARCH_REFLECTING: [
    "Checking if each theme has enough evidence…",
    "Identifying gaps in competitor coverage…",
    "Planning follow-up searches for weak spots…",
    "Validating citation coverage…",
  ],
  RESEARCH_SYNTHESIZING: [
    "Grading market opportunity against the rubric…",
    "Writing specific findings with citations…",
    "Drafting recommendation and risk summary…",
    "Finalizing your validation report…",
  ],
};

const PHASE_MILESTONE: Record<string, string> = {
  RESEARCHING: "Research pipeline initialized",
  RESEARCH_PLANNING: "Research plan ready",
  RESEARCH_SEARCHING: "Search pass complete — sources collected",
  RESEARCH_READING: "Evidence extracted from sources",
  RESEARCH_REFLECTING: "Evidence review complete",
  RESEARCH_SYNTHESIZING: "Findings structured for your report",
};

export interface ResearchActivityLine {
  id: string;
  text: string;
  done: boolean;
}

export function getActivityTemplates(phase: string): readonly string[] {
  return PHASE_ACTIVITY[phase] ?? [];
}

export function getPhaseMilestone(phase: string): string {
  if (PHASE_MILESTONE[phase]) return PHASE_MILESTONE[phase];
  const label =
    RESEARCH_PHASE_LABELS[phase as keyof typeof RESEARCH_PHASE_LABELS];
  return label ? `${label} — complete` : "Step complete";
}
