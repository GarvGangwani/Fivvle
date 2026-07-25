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
    <div
      ref={menuRef}
      className="absolute z-20"
      style={{ left: 24, bottom: 24 }}
    >
      {open ? (
        <div className="absolute bottom-full left-0 mb-0 min-w-[160px] rounded-md border-2 border-border-master bg-surface-card shadow-brutal-md">
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
        className="flex h-[32px] w-[32px] items-center justify-center rounded-none border-2 border-border-master bg-surface-card font-label-md text-label-md leading-none text-ink-primary shadow-brutal-sm hover:shadow-brutal-md"
        aria-label="Canvas options"
        aria-expanded={open}
        title="Canvas options"
      >
        ⋯
      </button>
    </div>
  );
}
