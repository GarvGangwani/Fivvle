"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { SAMPLE_REFINED } from "./shared";

const SLIDES = [
  {
    id: "hook",
    title: "Hook",
    prompt: "What’s the punchy opening line?",
    content: SAMPLE_REFINED.oneLiner,
  },
  {
    id: "who",
    title: "Who",
    prompt: "Who feels this pain every week?",
    content: SAMPLE_REFINED.audience,
  },
  {
    id: "pain",
    title: "Pain",
    prompt: "What are they escaping?",
    content: "Swipe fatigue, ghosting, and matches that go nowhere.",
  },
  {
    id: "edge",
    title: "Edge",
    prompt: "Why you vs Hinge/Tinder?",
    content: SAMPLE_REFINED.value,
  },
  {
    id: "bet",
    title: "The bet",
    prompt: "What will you test first?",
    content: SAMPLE_REFINED.test,
  },
] as const;

export function PitchDeckDemo() {
  const [unlocked, setUnlocked] = useState(1);
  const [viewIndex, setViewIndex] = useState(0);

  const slide = SLIDES[viewIndex];
  const isLocked = viewIndex >= unlocked;

  function unlockNext() {
    setUnlocked((u) => Math.min(SLIDES.length, u + 1));
    setViewIndex((i) => Math.min(SLIDES.length - 1, i + 1));
  }

  return (
    <div className="rd-demo">
      <p className="rd-demo-label">Concept 5</p>
      <h2 className="rd-demo-title">Pitch Deck Unlock</h2>
      <p className="rd-demo-desc">
        Five slides unlock in order. Each answer becomes a slide — founders think
        in pitches, not paragraphs.
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        {SLIDES.map((s, i) => (
          <button
            key={s.id}
            type="button"
            disabled={i >= unlocked}
            onClick={() => i < unlocked && setViewIndex(i)}
            className={`rd-chip ${viewIndex === i ? "rd-chip-selected" : ""} ${
              i >= unlocked ? "opacity-40" : ""
            }`}
          >
            {i + 1}. {s.title}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <div
          className="relative flex min-h-[280px] flex-col justify-between overflow-hidden rounded-2xl border border-[var(--fv-border)] p-6"
          style={{
            background:
              "linear-gradient(145deg, color-mix(in srgb, var(--fv-accent) 18%, var(--fv-surface)), var(--fv-surface-2))",
          }}
        >
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--fv-text-muted)]">
              Slide {viewIndex + 1} · {slide.title}
            </p>
            <h3 className="mt-4 text-xl font-bold leading-snug text-[var(--fv-text)] sm:text-2xl">
              {isLocked ? slide.prompt : slide.content}
            </h3>
          </div>
          <div className="flex items-center justify-between pt-6">
            <button
              type="button"
              className="rd-btn"
              disabled={viewIndex === 0}
              onClick={() => setViewIndex((i) => i - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              className="rd-btn"
              disabled={viewIndex >= unlocked - 1}
              onClick={() => setViewIndex((i) => i + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="rd-panel">
          {isLocked ? (
            <>
              <p className="mb-2 text-sm font-medium text-[var(--fv-text)]">
                {slide.prompt}
              </p>
              <textarea
                className="fv-input mb-3 min-h-[100px] w-full resize-y text-sm"
                placeholder="One or two sentences…"
              />
              <button type="button" className="rd-btn-primary w-full" onClick={unlockNext}>
                Unlock slide
              </button>
            </>
          ) : (
            <p className="text-sm text-[var(--fv-text-soft)]">
              This slide is locked in. Continue or review previous slides with the
              arrows.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
