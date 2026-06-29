"use client";

import { useState } from "react";

const CARDS = [
  {
    id: "psych",
    title: "Psychology-first",
    body: "Match on archetypes & behavior, not photos.",
    tag: "Positioning",
  },
  {
    id: "slow",
    title: "Slow dating",
    body: "One intentional match per week — anti-swipe.",
    tag: "Positioning",
  },
  {
    id: "blind",
    title: "Blind by design",
    body: "Photos unlock only after mutual interest.",
    tag: "Mechanic",
  },
  {
    id: "city",
    title: "City singles 25–35",
    body: "Dense markets where swipe fatigue is highest.",
    tag: "Audience",
  },
  {
    id: "ghost",
    title: "Anti-ghosting",
    body: "Structured follow-up prompts after each date.",
    tag: "Mechanic",
  },
] as const;

export function CardDraftDemo() {
  const [hand, setHand] = useState(() => CARDS.slice(0, 3));
  const [picked, setPicked] = useState<(typeof CARDS)[number][]>([]);
  const [turn, setTurn] = useState(1);

  function selectCard(card: (typeof CARDS)[number]) {
    setPicked((prev) => [...prev, card]);
    setHand(CARDS.slice(turn, turn + 3).length ? CARDS.slice(turn, turn + 3) : []);
    setTurn((t) => t + 1);
  }

  return (
    <div className="rd-demo">
      <p className="rd-demo-label">Concept 4</p>
      <h2 className="rd-demo-title">Card Draft</h2>
      <p className="rd-demo-desc">
        Each refine turn deals new cards — pick the angle that fits. Feels like
        deck-building, not messaging.
      </p>

      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--fv-text-muted)]">
          Turn {Math.min(turn, 3)} / 3
        </span>
        <span className="text-xs text-[var(--fv-text-soft)]">
          {picked.length} cards drafted
        </span>
      </div>

      {hand.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-3">
          {hand.map((card) => (
            <button
              key={card.id}
              type="button"
              onClick={() => selectCard(card)}
              className="group rd-panel text-left transition-transform hover:-translate-y-1 hover:border-[var(--fv-accent)]"
            >
              <span className="text-[10px] font-bold uppercase tracking-wide text-[var(--fv-accent)]">
                {card.tag}
              </span>
              <p className="mt-2 text-sm font-bold text-[var(--fv-text)]">
                {card.title}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                {card.body}
              </p>
              <span className="mt-3 inline-block text-[11px] font-semibold text-[var(--fv-accent)] opacity-0 transition-opacity group-hover:opacity-100">
                Draft this →
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="rd-panel text-center">
          <p className="text-sm font-semibold text-[var(--fv-text)]">
            Deck complete
          </p>
          <p className="mt-1 text-xs text-[var(--fv-text-muted)]">
            Your positioning stack is ready for research.
          </p>
        </div>
      )}

      {picked.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-[var(--fv-text-muted)]">
            Your stack
          </p>
          <div className="flex flex-wrap gap-2">
            {picked.map((card) => (
              <span key={card.id} className="rd-chip rd-chip-selected">
                {card.title}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
