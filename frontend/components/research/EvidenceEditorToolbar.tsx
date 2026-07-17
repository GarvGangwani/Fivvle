"use client";

import type { Editor } from "@tiptap/react";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  RemoveFormatting,
  Ban,
} from "lucide-react";

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

export function EvidenceEditorToolbar({ editor }: { editor: Editor | null }) {
  if (!editor) return null;

  const currentFontSize =
    (editor.getAttributes("textStyle").fontSize as string | undefined)?.replace(
      "px",
      "",
    ) ?? DEFAULT_FONT_SIZE;

  function applyFontSize(value: string) {
    if (!editor) return;
    if (value === DEFAULT_FONT_SIZE) {
      editor.chain().focus().unsetFontSize().run();
      return;
    }
    editor.chain().focus().setFontSize(`${value}px`).run();
  }

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

      <label className="sr-only" htmlFor="evidence-font-size">
        Font size
      </label>
      <select
        id="evidence-font-size"
        value={currentFontSize}
        onChange={(e) => applyFontSize(e.target.value)}
        className="h-8 border-2 border-border-master bg-surface-card px-1 font-mono text-mono-sm text-ink-primary"
      >
        {FONT_SIZES.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>

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
    </div>
  );
}
