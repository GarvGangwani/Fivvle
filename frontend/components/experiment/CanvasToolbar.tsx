"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  onReset: () => void;
  onFitView: () => void;
};

export function CanvasToolbar({ onReset, onFitView }: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  return (
    <div ref={menuRef} className="absolute bottom-6 left-6 z-20 flex flex-col items-start gap-2">
      {open ? (
        <div className="rounded-md border-2 border-border-master bg-surface-card shadow-brutal-md">
          <button
            type="button"
            onClick={() => {
              onFitView();
              setOpen(false);
            }}
            className="block w-full border-b-2 border-border-master px-4 py-2 text-left font-label-md text-label-sm uppercase text-ink-primary hover:bg-surface-muted"
          >
            Fit view
          </button>
          <button
            type="button"
            onClick={() => {
              onReset();
              setOpen(false);
            }}
            className="block w-full px-4 py-2 text-left font-label-md text-label-sm uppercase text-ink-primary hover:bg-surface-muted"
          >
            Reset layout
          </button>
        </div>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="rounded-sm border-2 border-border-master bg-surface-card px-3 py-2 font-label-md text-label-md uppercase text-ink-primary shadow-brutal-sm hover:shadow-brutal-md"
        aria-label="Canvas options"
        aria-expanded={open}
      >
        ⋯
      </button>
    </div>
  );
}
