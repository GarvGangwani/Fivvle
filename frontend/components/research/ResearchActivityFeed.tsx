"use client";

import { useEffect, useRef } from "react";
import { Check, Loader2 } from "lucide-react";
import type { ResearchActivityLine } from "@/lib/research-activity";

interface ResearchActivityFeedProps {
  lines: ResearchActivityLine[];
  isComplete?: boolean;
}

export function ResearchActivityFeed({
  lines,
  isComplete = false,
}: ResearchActivityFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines]);

  if (lines.length === 0) return null;

  return (
    <div className="fv-research-activity" aria-live="polite" aria-busy={!isComplete}>
      <p className="fv-research-activity-title">What Fivvle is doing</p>
      <div ref={scrollRef} className="fv-research-activity-scroll">
        <ul className="fv-research-activity-list">
          {lines.map((line) => (
            <li
              key={line.id}
              className={`fv-research-activity-item ${
                line.done
                  ? "fv-research-activity-item--done"
                  : "fv-research-activity-item--active"
              }`}
            >
              <span className="fv-research-activity-icon" aria-hidden>
                {line.done ? (
                  <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                ) : (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                )}
              </span>
              <span className="fv-research-activity-text">{line.text}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
