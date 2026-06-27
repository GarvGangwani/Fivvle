"use client";

import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
import { SAMPLE_PITCH, SAMPLE_REFINED } from "./shared";

const SAMPLE_CLARITY = `What specific frustration with current dating apps are you solving?
→ Superficiality of photo-first apps; Decision fatigue from endless swiping

How would this app make money?
→ Subscription: monthly fee for unlimited matching and verified badge`;

/** Live refinement thread styling — wired in ChatInterface. */
export function RefinementPeakDemo() {
  const refinedText = `Researching: ${SAMPLE_REFINED.oneLiner}`;

  return (
    <div className="rd-demo">
      <div className="rd-demo-header">
        <p className="rd-demo-label">Concept A · Alternate</p>
        <h2 className="rd-demo-title">Refinement Peak</h2>
        <p className="rd-demo-desc">
          Timeline journey: your raw idea as an achievement, Q&amp;A as clarity
          chips, refined hypothesis as a before → after upgrade.
        </p>
      </div>

      <div className="mx-auto max-w-[720px] space-y-0 py-4">
        <RefinementThreadMessage
          id="demo-spark"
          role="user"
          content={SAMPLE_PITCH}
          isSparkIdea
          demoUserLabel="Chaitanaya"
          variant="peak"
        />
        <RefinementThreadMessage
          id="demo-clarity"
          role="user"
          content={SAMPLE_CLARITY}
          clarityRound={1}
          demoUserLabel="Chaitanaya"
          variant="peak"
        />
        <RefinementThreadMessage
          id="demo-refined"
          role="assistant"
          content={refinedText}
          turnKind="refinement_finalize"
          originalIdea={SAMPLE_PITCH}
          variant="peak"
        />
      </div>
    </div>
  );
}
