"use client";

import { useEffect, useRef, useState } from "react";
import type { Editor } from "@tiptap/react";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  RemoveFormatting,
  Ban,
  ChevronDown,
} from "lucide-react";
import type { SaveStatus } from "@/components/research/EvidenceReportEditor";

const FONT_SIZES = ["12", "14", "16", "18", "24"] as const;
const DEFAULT_FONT_SIZE = "16";

const TEXT_COLORS: { color: string; label: string }[] = [
  { color: "#000000", label: "Black text" },
  { color: "#4f46e5", label: "Indigo text" },
  { color: "#EF4444", label: "Red text" },
  { color: "#22C55E", label: "Green text" },
];

const HIGHLIGHT_COLORS: { color: string; label: string }[] = [
  { color: "#FFFF00", label: "Yellow highlight" },
  { color: "#4f46e5", label: "Indigo highlight" },
  { color: "#EF4444", label: "Red highlight" },
  { color: "#22C55E", label: "Green highlight" },
];

function ToolbarButton({
  onClick,
  active = false,
  disabled = false,
  label,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={active}
      title={label}
      className={`flex h-8 w-8 items-center justify-center border-2 border-border-master transition-shadow disabled:opacity-40 ${
        active
          ? "bg-brand-primary text-ink-inverse"
          : "bg-surface-card text-ink-primary hover:shadow-brutal-sm"
      }`}
    >
      {children}
    </button>
  );
}

function SwatchButton({
  color,
  active,
  onClick,
  label,
}: {
  color: string;
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      title={label}
      className={`h-7 w-7 border-2 transition-shadow hover:shadow-brutal-sm ${
        active ? "border-brand-primary" : "border-border-master"
      }`}
      style={{ backgroundColor: color }}
    />
  );
}

function Divider() {
  return <span aria-hidden="true" className="mx-1 h-6 w-px bg-border-master" />;
}

/**
 * Font-size picker. Its own component so the open/click-outside state lives
 * below the toolbar's `if (!editor) return null` early exit (hooks can't sit
 * above a conditional return). The menu is absolutely positioned + z-20 so it
 * layers over the editor body below.
 */
function FontSizeDropdown({ editor }: { editor: Editor }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const currentFontSize =
    (editor.getAttributes("textStyle").fontSize as string | undefined)?.replace(
      "px",
      "",
    ) ?? DEFAULT_FONT_SIZE;

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  function applyFontSize(value: string) {
    if (value === DEFAULT_FONT_SIZE) {
      editor.chain().focus().unsetFontSize().run();
    } else {
      editor.chain().focus().setFontSize(`${value}px`).run();
    }
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Font size"
        title="Font size"
        className="flex h-8 items-center gap-1 border-2 border-border-master bg-surface-card px-2 font-mono text-mono-sm text-ink-primary transition-shadow hover:shadow-brutal-sm"
      >
        <span className="tabular-nums">{currentFontSize}</span>
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div
          role="listbox"
          aria-label="Font size"
          className="absolute left-0 top-full z-20 mt-1 flex w-16 flex-col border-2 border-border-master bg-surface-card shadow-brutal-sm"
        >
          {FONT_SIZES.map((size) => (
            <button
              key={size}
              type="button"
              role="option"
              aria-selected={size === currentFontSize}
              onClick={() => applyFontSize(size)}
              className={`px-2 py-1.5 text-left font-mono text-mono-sm ${
                size === currentFontSize
                  ? "bg-brand-primary text-ink-inverse"
                  : "text-ink-primary hover:bg-surface-muted"
              }`}
            >
              {size}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function saveStatusLabel(status: SaveStatus, lastSavedAt: Date | null): string {
  switch (status) {
    case "saving":
      return "Saving…";
    case "unsaved":
      return "Unsaved changes";
    case "error":
      return "Save failed — will retry on next edit";
    case "saved":
      return lastSavedAt
        ? `Saved • ${lastSavedAt.toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
          })}`
        : "Saved";
    default:
      return "";
  }
}

export function EvidenceEditorToolbar({
  editor,
  status,
  lastSavedAt,
}: {
  editor: Editor | null;
  status: SaveStatus;
  lastSavedAt: Date | null;
}) {
  if (!editor) return null;

  return (
    <div className="flex flex-wrap items-center gap-1 border-2 border-border-master bg-surface-card p-2 shadow-brutal-sm">
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        active={editor.isActive("bold")}
        label="Bold"
      >
        <Bold className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        active={editor.isActive("italic")}
        label="Italic"
      >
        <Italic className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        active={editor.isActive("underline")}
        label="Underline"
      >
        <UnderlineIcon className="h-4 w-4" />
      </ToolbarButton>

      <Divider />

      <FontSizeDropdown editor={editor} />

      <Divider />

      <div className="flex items-center gap-1" role="group" aria-label="Text color">
        {TEXT_COLORS.map(({ color, label }) => (
          <SwatchButton
            key={color}
            color={color}
            label={label}
            active={editor.isActive("textStyle", { color })}
            onClick={() => editor.chain().focus().setColor(color).run()}
          />
        ))}
        <ToolbarButton
          onClick={() => editor.chain().focus().unsetColor().run()}
          label="Default text color"
        >
          <Ban className="h-4 w-4" />
        </ToolbarButton>
      </div>

      <Divider />

      <div
        className="flex items-center gap-1"
        role="group"
        aria-label="Highlight color"
      >
        {HIGHLIGHT_COLORS.map(({ color, label }) => (
          <SwatchButton
            key={color}
            color={color}
            label={label}
            active={editor.isActive("highlight", { color })}
            onClick={() =>
              editor.chain().focus().toggleHighlight({ color }).run()
            }
          />
        ))}
      </div>

      <Divider />

      <ToolbarButton
        onClick={() =>
          editor.chain().focus().clearNodes().unsetAllMarks().run()
        }
        label="Clear formatting"
      >
        <RemoveFormatting className="h-4 w-4" />
      </ToolbarButton>

      <div className="ml-auto flex items-center gap-1">
        <Divider />
        <span
          aria-live="polite"
          className={`whitespace-nowrap px-1 font-mono text-mono-sm uppercase ${
            status === "error" ? "text-status-critical" : "text-ink-tertiary"
          }`}
        >
          {saveStatusLabel(status, lastSavedAt)}
        </span>
      </div>
    </div>
  );
}
