"use client";

import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import type { LaunchChannel } from "@/lib/api-launch-kit";
import { CHANNEL_LABELS, LAUNCH_CHANNELS } from "@/lib/launch-labels";

type Props = {
  open: boolean;
  anchorRef: RefObject<HTMLElement | null>;
  current: LaunchChannel;
  onSelect: (channel: LaunchChannel) => void;
  onClose: () => void;
};

/**
 * Brutalist channel picker — portaled to document.body, Escape + outside-click close.
 */
export function ChannelSelectPopover({
  open,
  anchorRef,
  current,
  onSelect,
  onClose,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; width: number }>({
    top: 0,
    left: 0,
    width: 240,
  });

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    setPos({
      top: rect.bottom + 8 + window.scrollY,
      left: rect.left + window.scrollX,
      width: Math.max(rect.width, 220),
    });
  }, [open, anchorRef]);

  useEffect(() => {
    if (!open) return;

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function onPointer(e: MouseEvent) {
      const target = e.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    }

    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onPointer);
    };
  }, [open, onClose, anchorRef]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={panelRef}
      role="listbox"
      aria-label="Select first channel"
      className="z-[80] border-2 border-border-master bg-surface-card shadow-brutal-md"
      style={{
        position: "absolute",
        top: pos.top,
        left: pos.left,
        width: pos.width,
        borderRadius: 0,
      }}
    >
      <ul className="max-h-64 overflow-y-auto py-1">
        {LAUNCH_CHANNELS.map((channel) => {
          const selected = channel === current;
          return (
            <li key={channel}>
              <button
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  onSelect(channel);
                  onClose();
                }}
                className={`flex w-full items-center justify-between px-4 py-2 text-left font-label-md text-label-sm uppercase tracking-wider transition-colors ${
                  selected
                    ? "bg-brutalist-yellow text-ink-primary"
                    : "text-ink-primary hover:bg-surface-elevated"
                }`}
              >
                {CHANNEL_LABELS[channel]}
                {selected ? (
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 16 }}
                    aria-hidden="true"
                  >
                    check
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ul>
    </div>,
    document.body,
  );
}
