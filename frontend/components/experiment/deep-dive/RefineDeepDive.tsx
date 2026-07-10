"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";
import { useEffect, useState } from "react";
import { getExperiment } from "@/lib/api";

type Props = {
  experimentId: string;
};

export function RefineDeepDive({ experimentId }: Props) {
  const [rawIdeaEmpty, setRawIdeaEmpty] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void getExperiment(experimentId)
      .then((exp) => {
        if (!cancelled) setRawIdeaEmpty(!exp.raw_idea?.trim());
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  return (
    <div className="h-[calc(100vh-64px)] border-t-2 border-border-master bg-canvas-bg">
      {rawIdeaEmpty ? (
        <div className="mx-6 mt-4 border-2 border-brutalist-yellow bg-brutalist-yellow/20 p-3">
          <p className="font-body text-body-sm">
            <strong>Add your idea in Spark first.</strong> Refine works best
            with a clear starting point.
          </p>
        </div>
      ) : null}
      <ChatInterface experimentId={experimentId} />
    </div>
  );
}
