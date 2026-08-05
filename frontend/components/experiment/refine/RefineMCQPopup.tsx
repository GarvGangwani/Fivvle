"use client";

import {
  useEffect,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { createPortal } from "react-dom";
import { getCanvasAccentPortalTarget } from "@/components/experiment/canvas-accent";

export type MCQAnswer = {
  combinedText: string;
  selectedIndices: number[];
  customAddedText: string | null;
};

export type MCQPopupPosition = { x: number; y: number };

type Props = {
  question: string;
  options: string[];
  turnNumber: number;
  /** Null = center of viewport on mount. */
  initialPosition: MCQPopupPosition | null;
  onPositionChange: (position: MCQPopupPosition) => void;
  onAnswer: (answer: MCQAnswer) => void;
  onDismiss: () => void;
};

const POPUP_WIDTH = 384;
const POPUP_HEIGHT_APPROX = 500;
const MAX_POPUP_OPTIONS = 4;

export function computeCenteredMcqPosition(): MCQPopupPosition {
  return {
    x: Math.max(0, (window.innerWidth - POPUP_WIDTH) / 2),
    y: Math.max(0, (window.innerHeight - POPUP_HEIGHT_APPROX) / 2),
  };
}

export function RefineMCQPopup({
  question,
  options,
  turnNumber,
  initialPosition,
  onPositionChange,
  onAnswer,
  onDismiss,
}: Props) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set(),
  );
  const [customText, setCustomText] = useState("");
  const [customFocused, setCustomFocused] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<MCQPopupPosition>(
    () => initialPosition ?? computeCenteredMcqPosition(),
  );
  const positionRef = useRef(position);
  positionRef.current = position;
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const visibleOptions = options.slice(0, MAX_POPUP_OPTIONS);
  const nextLetter = String.fromCharCode(65 + visibleOptions.length);
  const customTrimmed = customText.trim();
  const hasCustom = customTrimmed.length > 0;
  const totalSelected = selectedIndices.size + (hasCustom ? 1 : 0);
  const canSubmit = totalSelected > 0;

  useEffect(() => {
    setSelectedIndices(new Set());
    setCustomText("");
    setCustomFocused(false);
  }, [question, options]);

  const toggleOption = (index: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const handleSubmit = () => {
    const parts: string[] = [];
    Array.from(selectedIndices)
      .sort((a, b) => a - b)
      .forEach((i) => {
        parts.push(visibleOptions[i]);
      });
    if (hasCustom) parts.push(customTrimmed);
    if (parts.length === 0) return;
    onPositionChange(positionRef.current);
    onAnswer({
      combinedText: parts.join(" · "),
      selectedIndices: Array.from(selectedIndices).sort((a, b) => a - b),
      customAddedText: hasCustom ? customTrimmed : null,
    });
  };

  const handleDismiss = () => {
    onPositionChange(positionRef.current);
    onDismiss();
  };

  const handleDragStart = (e: ReactMouseEvent) => {
    if (!popupRef.current) return;
    const rect = popupRef.current.getBoundingClientRect();
    dragOffset.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
    setIsDragging(true);
  };

  useEffect(() => {
    if (!isDragging) return;
    const handleMove = (e: MouseEvent) => {
      const next = {
        x: Math.max(
          0,
          Math.min(
            window.innerWidth - POPUP_WIDTH,
            e.clientX - dragOffset.current.x,
          ),
        ),
        y: Math.max(
          0,
          Math.min(window.innerHeight - 100, e.clientY - dragOffset.current.y),
        ),
      };
      positionRef.current = next;
      setPosition(next);
    };
    const handleUp = () => {
      setIsDragging(false);
      onPositionChange(positionRef.current);
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [isDragging, onPositionChange]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={popupRef}
      style={{ left: position.x, top: position.y }}
      className="fixed z-[85] w-96 rounded-md bg-accent text-ink-inverse border-2 border-border-master shadow-brutal-lg"
    >
      <div
        onMouseDown={handleDragStart}
        className={`flex items-center justify-between px-4 py-3 border-b-2 border-ink-inverse/20 select-none ${
          isDragging ? "cursor-grabbing" : "cursor-grab"
        }`}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-brutalist-yellow animate-pulse" />
          <span className="font-mono text-mono-sm uppercase tracking-wider">
            CRITICAL INQUIRY · TURN {turnNumber}
          </span>
        </div>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss"
          className="p-1 hover:bg-ink-inverse/10"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 16 }}
            aria-hidden="true"
          >
            close
          </span>
        </button>
      </div>

      <div className="p-5">
        <p className="font-body text-body-md leading-relaxed mb-4">{question}</p>

        {totalSelected > 1 ? (
          <p className="font-mono text-mono-sm uppercase text-brutalist-yellow mb-3">
            {totalSelected} SELECTED
          </p>
        ) : null}

        <div className="space-y-2">
          {visibleOptions.map((option, i) => {
            const letter = String.fromCharCode(65 + i);
            const isSelected = selectedIndices.has(i);
            return (
              <button
                key={`${letter}-${option}`}
                type="button"
                onClick={() => toggleOption(i)}
                className={`w-full flex items-stretch rounded-sm border-2 transition-all ${
                  isSelected
                    ? "border-brutalist-yellow bg-brutalist-yellow text-ink-primary"
                    : "border-ink-inverse/40 bg-ink-inverse/10 text-ink-inverse fv-brutal-hover"
                }`}
              >
                <div
                  className={`px-3 py-3 border-r-2 flex items-center ${
                    isSelected ? "border-ink-primary" : "border-ink-inverse"
                  }`}
                >
                  {isSelected ? (
                    <span
                      className="material-symbols-outlined"
                      style={{ fontSize: 18 }}
                      aria-hidden="true"
                    >
                      check
                    </span>
                  ) : (
                    <span className="font-mono text-mono-sm font-bold">
                      {letter}
                    </span>
                  )}
                </div>
                <div className="px-4 py-3 text-left flex-1">
                  <span className="font-label-md text-label-md uppercase tracking-wider">
                    {option}
                  </span>
                </div>
              </button>
            );
          })}

          <div
            className={`w-full flex items-stretch rounded-sm border-2 transition-all ${
              hasCustom
                ? "border-brutalist-yellow bg-brutalist-yellow text-ink-primary"
                : customFocused
                  ? "border-brutalist-yellow bg-ink-inverse/15 text-ink-inverse"
                  : "border-ink-inverse/40 border-dashed bg-ink-inverse/10 text-ink-inverse"
            }`}
          >
            <div
              className={`px-3 py-3 border-r-2 flex items-center shrink-0 ${
                hasCustom ? "border-ink-primary" : "border-ink-inverse"
              }`}
            >
              {hasCustom ? (
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: 18 }}
                  aria-hidden="true"
                >
                  check
                </span>
              ) : (
                <span className="font-mono text-mono-sm font-bold">
                  {nextLetter}
                </span>
              )}
            </div>
            <input
              type="text"
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              onFocus={() => setCustomFocused(true)}
              onBlur={() => setCustomFocused(false)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && canSubmit) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Or write your own answer..."
              className={`flex-1 px-4 py-3 bg-transparent border-none outline-none font-label-md text-label-md uppercase tracking-wider ${
                hasCustom
                  ? "text-ink-primary placeholder:text-ink-primary/40"
                  : "text-ink-inverse placeholder:text-ink-inverse/40"
              }`}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="mt-4 w-full rounded-sm bg-brutalist-yellow text-ink-primary px-6 py-3 border-2 border-border-master font-label-md text-label-md uppercase tracking-wider shadow-brutal-md hover:shadow-brutal-lg hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 18 }}
            aria-hidden="true"
          >
            arrow_forward
          </span>
          {totalSelected === 0
            ? "SELECT AN OPTION"
            : totalSelected === 1
              ? "CONFIRM"
              : `CONFIRM (${totalSelected} SELECTED)`}
        </button>
      </div>
    </div>,
    getCanvasAccentPortalTarget(),
  );
}
