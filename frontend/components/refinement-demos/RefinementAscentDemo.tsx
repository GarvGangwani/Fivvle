"use client";

import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
import { PressureTestSection } from "@/components/refinement/PressureTestSection";
import { SAMPLE_PITCH, SAMPLE_REFINED } from "./shared";

const SAMPLE_CLARITY = `What specific frustration with current dating apps are you solving?
→ Superficiality of photo-first apps; Decision fatigue from endless swiping

How would this app make money?
→ Subscription: monthly fee for unlimited matching and verified badge`;

/** Live refinement thread styling — wired in ChatInterface. */
export function RefinementAscentDemo() {
  const refinedText = `Researching: ${SAMPLE_REFINED.oneLiner}`;

  return (
    <div className="rd-demo">
      <div className="rd-demo-header">
        <p className="rd-demo-label">Concept B · Shipped in app</p>
        <h2 className="rd-demo-title">Refinement Ascent</h2>
        <p className="rd-demo-desc">
          Magazine-style story arc: big typographic hero, pull quotes for
          answers, finale spread for the upgraded hypothesis.
        </p>
      </div>

      <article className="ra-story">
        <RefinementThreadMessage
          id="demo-spark"
          role="user"
          content={SAMPLE_PITCH}
          isSparkIdea
          demoUserLabel="Chaitanaya"
        />
        <PressureTestSection
          blocks={[
            {
              messageId: "demo-clarity",
              question:
                "What specific frustration with current dating apps are you solving?",
              answers: [
                "Superficiality of photo-first apps",
                "Decision fatigue from endless swiping",
              ],
            },
            {
              messageId: "demo-clarity",
              question: "How would this app make money?",
              answers: [
                "Subscription — monthly fee for unlimited matching and verified badge",
              ],
            },
          ]}
          contentKey={SAMPLE_CLARITY}
          messageContentById={{ "demo-clarity": SAMPLE_CLARITY }}
          canEditMessage={() => false}
          onEdit={async () => {}}
        />
        <RefinementThreadMessage
          id="demo-refined"
          role="assistant"
          content={refinedText}
          turnKind="refinement_finalize"
          originalIdea={SAMPLE_PITCH}
        />
      </article>
    </div>
  );
}
