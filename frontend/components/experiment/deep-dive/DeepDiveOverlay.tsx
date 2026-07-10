"use client";

import { useEffect } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  act: "evidence" | "launch" | "signal";
  experimentId: string;
};

export function DeepDiveOverlay({ isOpen, onClose, act }: Props) {
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[70] bg-canvas-bg">
      <div className="flex h-16 items-center justify-between border-b-2 border-border-master px-6">
        <button
          type="button"
          onClick={onClose}
          className="font-label-md text-label-sm uppercase text-ink-primary"
        >
          ← Back to canvas
        </button>
        <h2 className="font-display text-display-sm uppercase text-ink-primary">
          {act} deep-dive
        </h2>
        <button
          type="button"
          onClick={onClose}
          className="font-label-md text-label-sm uppercase text-ink-primary"
          aria-label="Close overlay"
        >
          ✕
        </button>
      </div>
      <div className="p-24 text-center">
        <div className="mb-2 font-label-md text-label-md uppercase text-brand-primary">
          COMING IN STEP 6
        </div>
        <h2 className="font-display text-display-lg uppercase text-ink-primary">
          {act} deep-dive
        </h2>
      </div>
    </div>
  );
}
