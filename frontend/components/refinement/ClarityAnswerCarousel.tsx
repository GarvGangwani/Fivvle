"use client";

import { useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";

interface ClarityAnswerCarouselProps {
  blocks: SourcedClarityQaBlock[];
  contentKey: string;
  index: number;
  onIndexChange: (index: number) => void;
}

export function ClarityAnswerCarousel({
  blocks,
  contentKey,
  index,
  onIndexChange,
}: ClarityAnswerCarouselProps) {
  const total = blocks.length;
  const safeIndex = total > 0 ? Math.min(index, total - 1) : 0;
  const block = blocks[safeIndex];

  useEffect(() => {
    onIndexChange(0);
  }, [contentKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (index >= total && total > 0) {
      onIndexChange(total - 1);
    }
  }, [index, total, onIndexChange]);

  if (!block) return null;

  const canPrev = safeIndex > 0;
  const canNext = safeIndex < total - 1;

  return (
    <div className="ra-qa-carousel">
      {total > 1 && (
        <nav className="ra-qa-nav" aria-label="Question navigation">
          <button
            type="button"
            className="ra-qa-nav-btn"
            onClick={() => onIndexChange(Math.max(0, safeIndex - 1))}
            disabled={!canPrev}
            aria-label="Previous question"
          >
            <ChevronLeft aria-hidden />
          </button>
          <span className="ra-qa-nav-count" aria-live="polite">
            {safeIndex + 1} of {total}
          </span>
          <button
            type="button"
            className="ra-qa-nav-btn"
            onClick={() => onIndexChange(Math.min(total - 1, safeIndex + 1))}
            disabled={!canNext}
            aria-label="Next question"
          >
            <ChevronRight aria-hidden />
          </button>
        </nav>
      )}

      <article className="ra-qa-card">
        <p className="ra-qa-q">{block.question}</p>
        <ul className="ra-qa-list">
          {block.answers.map((answer) => (
            <li
              key={`${block.messageId}-${block.question}-${answer}`}
              className="ra-qa-list-item"
            >
              {answer}
            </li>
          ))}
        </ul>
      </article>
    </div>
  );
}
