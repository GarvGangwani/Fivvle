"use client";

import { useEffect, useRef, useState } from "react";
import type { ResearchStatus } from "@/lib/types";
import { resolveResearchPhase } from "@/lib/research-status";
import {
  getActivityTemplates,
  getPhaseMilestone,
  type ResearchActivityLine,
} from "@/lib/research-activity";

const TICK_MS = 2_800;

export function useResearchActivityLog(
  status: ResearchStatus | null,
  isComplete: boolean,
  isRunning: boolean,
): ResearchActivityLine[] {
  const [lines, setLines] = useState<ResearchActivityLine[]>([]);
  const seenMilestonesRef = useRef<Set<string>>(new Set());
  const startedRef = useRef(false);

  const currentPhase = resolveResearchPhase(status?.status);
  const phasesCompleted = status?.phases_completed ?? [];

  useEffect(() => {
    if (!isRunning && !isComplete) {
      startedRef.current = false;
      seenMilestonesRef.current = new Set();
      setLines([]);
    }
  }, [isRunning, isComplete]);

  useEffect(() => {
    if (!isRunning || startedRef.current) return;
    startedRef.current = true;
    setLines([
      {
        id: "boot",
        text: "Starting deep research on your idea…",
        done: true,
      },
    ]);
  }, [isRunning]);

  useEffect(() => {
    if (!status) return;

    const additions: ResearchActivityLine[] = [];
    for (const phase of phasesCompleted) {
      if (seenMilestonesRef.current.has(phase)) continue;
      seenMilestonesRef.current.add(phase);
      additions.push({
        id: `milestone-${phase}`,
        text: getPhaseMilestone(phase),
        done: true,
      });
    }

    if (additions.length === 0) return;

    setLines((prev) => {
      const withoutActive = prev
        .filter((line) => line.id !== "active")
        .map((line) => ({ ...line, done: true }));
      return [...withoutActive, ...additions];
    });
  }, [phasesCompleted, status]);

  useEffect(() => {
    if (!isRunning || isComplete) return;

    const templates = getActivityTemplates(currentPhase);
    if (templates.length === 0) {
      const fallback = status?.phase_label?.trim();
      if (!fallback) return;
      setLines((prev) => {
        const withoutActive = prev.filter((line) => line.id !== "active");
        return [
          ...withoutActive,
          { id: "active", text: fallback, done: false },
        ];
      });
      return;
    }

    let tick = 0;

    function setActiveLine(text: string) {
      setLines((prev) => {
        const withoutActive = prev.filter((line) => line.id !== "active");
        return [...withoutActive, { id: "active", text, done: false }];
      });
    }

    setActiveLine(templates[0] ?? "");

    const intervalId = window.setInterval(() => {
      tick = (tick + 1) % templates.length;
      setActiveLine(templates[tick] ?? "");
    }, TICK_MS);

    return () => window.clearInterval(intervalId);
  }, [currentPhase, isRunning, isComplete, status?.phase_label]);

  useEffect(() => {
    if (!isComplete) return;
    setLines((prev) => {
      const finalized = prev
        .filter((line) => line.id !== "complete" && line.id !== "active")
        .map((line) => ({ ...line, done: true }));
      return [
        ...finalized,
        { id: "complete", text: "Validation report ready", done: true },
      ];
    });
  }, [isComplete]);

  return lines;
}
