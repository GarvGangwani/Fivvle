"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import {
  EditorContent,
  useEditor,
  type Editor,
  type JSONContent,
} from "@tiptap/react";
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextStyle from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import Highlight from "@tiptap/extension-highlight";
import { RefreshCw } from "lucide-react";
import {
  EditedDocVersionConflict,
  getEditedDoc,
  patchEditedDoc,
} from "@/lib/api";
import type { RefCitation } from "@/lib/types";
import { FontSize } from "@/lib/tiptap-font-size";
import { useToast } from "@/components/ui/ToastProvider";
import { EvidenceEditorToolbar } from "@/components/research/EvidenceEditorToolbar";
import "./evidence-editor.css";

const AUTOSAVE_DEBOUNCE_MS = 1200;
const REF_FLASH_MS = 1500;

export type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";

/** Question blocks are H2 rendered as "Q<N>. …" by PR 1's renderer. */
const QUESTION_HEADING_RE = /^Q(\d+)\./;

/** Imperative surface the chat pane calls to scroll + flash a report anchor. */
export interface EvidenceReportEditorHandle {
  focusReference: (anchor: RefCitation) => void;
}

/** Meta channel for the transient ref-highlight decoration. */
const refHighlightKey = new PluginKey("evidence-ref-highlight");

/**
 * A ProseMirror plugin that renders a single transient inline highlight. A
 * `{ from, to }` meta sets it; a `{ clear: true }` meta removes it. The
 * decoration maps through subsequent edits so it survives concurrent typing
 * until it's cleared.
 */
const RefHighlight = Extension.create({
  name: "evidenceRefHighlight",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: refHighlightKey,
        state: {
          init: () => DecorationSet.empty,
          apply(tr, old) {
            const meta = tr.getMeta(refHighlightKey) as
              | { from: number; to: number }
              | { clear: true }
              | undefined;
            if (meta) {
              if ("clear" in meta) return DecorationSet.empty;
              return DecorationSet.create(tr.doc, [
                Decoration.inline(meta.from, meta.to, {
                  class: "evidence-ref-flash",
                }),
              ]);
            }
            return old.map(tr.mapping, tr.doc);
          },
        },
        props: {
          decorations(state) {
            return refHighlightKey.getState(state) as DecorationSet;
          },
        },
      }),
    ];
  },
});

/**
 * Resolve a ref anchor to an inline document range, or null if not found.
 * - question: the H2 whose text starts with "Q<N>." for the matching N
 * - limitation: the "Research Limitations" H1
 * - competitor: an exact H3 name match, else the first inline text occurrence
 * (section refs never navigate the editor — scores were removed from the doc)
 */
function findRefRange(
  editor: Editor,
  anchor: RefCitation,
): { from: number; to: number } | null {
  const doc = editor.state.doc;
  let found: { from: number; to: number } | null = null;

  if (anchor.kind === "question") {
    const num = anchor.value.replace(/^q/i, "");
    doc.descendants((node, pos) => {
      if (found) return false;
      if (node.type.name === "heading" && node.attrs.level === 2) {
        const match = QUESTION_HEADING_RE.exec(node.textContent);
        if (match && match[1] === num) {
          found = { from: pos + 1, to: pos + 1 + node.content.size };
          return false;
        }
      }
      return true;
    });
    return found;
  }

  if (anchor.kind === "limitation") {
    doc.descendants((node, pos) => {
      if (found) return false;
      if (
        node.type.name === "heading" &&
        node.attrs.level === 1 &&
        /research limitations/i.test(node.textContent)
      ) {
        found = { from: pos + 1, to: pos + 1 + node.content.size };
        return false;
      }
      return true;
    });
    return found;
  }

  if (anchor.kind === "competitor") {
    const name = anchor.value.trim().toLowerCase();
    if (!name) return null;
    // First preference: an H3 heading that is exactly the competitor name.
    doc.descendants((node, pos) => {
      if (found) return false;
      if (
        node.type.name === "heading" &&
        node.attrs.level === 3 &&
        node.textContent.trim().toLowerCase() === name
      ) {
        found = { from: pos + 1, to: pos + 1 + node.content.size };
        return false;
      }
      return true;
    });
    if (found) return found;
    // Fallback: the first inline text occurrence of the name.
    doc.descendants((node, pos) => {
      if (found) return false;
      if (node.isText && node.text) {
        const idx = node.text.toLowerCase().indexOf(name);
        if (idx !== -1) {
          found = { from: pos + idx, to: pos + idx + anchor.value.length };
          return false;
        }
      }
      return true;
    });
    return found;
  }

  return null;
}

/**
 * Walk to the nearest heading of level <= 2 that starts at/before the selection
 * anchor. PR 1's renderer emits question blocks as H2 whose text starts with
 * "Q<N>." and every other section as H1. So: an H1 (a different section) resets
 * to null; a matching H2 sets the (lowercase) question id. Founder-edited
 * headings that drop the "Q<N>." prefix resolve to null (accepted fallback).
 */
function resolveQuestionId(editor: Editor, from: number): string | null {
  let questionId: string | null = null;
  editor.state.doc.nodesBetween(0, from, (node) => {
    if (node.type.name !== "heading") return;
    const level = node.attrs.level as number;
    if (level > 2) return;
    if (level === 1) {
      questionId = null;
      return;
    }
    const match = QUESTION_HEADING_RE.exec(node.textContent);
    questionId = match ? `q${match[1]}` : null;
  });
  return questionId;
}

export interface EvidenceSelection {
  text: string;
  question_id: string | null;
}

interface EvidenceReportEditorProps {
  experimentId: string;
  /** Lifts edited-doc-behind-regen so the panel can render the banner above the header. */
  onEditedDocBehindChange?: (behind: boolean) => void;
  /**
   * Lifts the current text selection up so the chat pane can anchor a question.
   * Fires null when the selection is empty (from === to) or whitespace-only.
   */
  onSelectionChange?: (selection: EvidenceSelection | null) => void;
}

export const EvidenceReportEditor = forwardRef<
  EvidenceReportEditorHandle,
  EvidenceReportEditorProps
>(function EvidenceReportEditor(
  { experimentId, onEditedDocBehindChange, onSelectionChange },
  ref,
) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const versionRef = useRef(0);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Underline,
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      FontSize,
      RefHighlight,
    ],
    editorProps: {
      attributes: {
        class: "evidence-prose",
      },
    },
  });

  const runSave = useCallback(async () => {
    if (!editor) return;
    setStatus("saving");
    try {
      const resp = await patchEditedDoc(experimentId, {
        doc: editor.getJSON(),
        base_version: versionRef.current,
      });
      versionRef.current = resp.version;
      onEditedDocBehindChange?.(resp.edited_doc_behind_regeneration);
      setLastSavedAt(new Date());
      setStatus("saved");
    } catch (err) {
      if (err instanceof EditedDocVersionConflict) {
        try {
          const fresh = await getEditedDoc(experimentId);
          editor.commands.setContent(fresh.doc as JSONContent, false);
          versionRef.current = fresh.version;
          onEditedDocBehindChange?.(fresh.edited_doc_behind_regeneration);
          toast("Report was updated elsewhere — reloaded", "info");
          setStatus("saved");
        } catch {
          toast("Could not reload the latest report.", "error");
          setStatus("error");
        }
        return;
      }
      toast("Could not save your changes. Retrying on next edit.", "error");
      setStatus("error");
    }
  }, [editor, experimentId, onEditedDocBehindChange, toast]);

  const scheduleSave = useCallback(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      void runSave();
    }, AUTOSAVE_DEBOUNCE_MS);
  }, [runSave]);

  useEffect(() => {
    if (!editor) return;
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    (async () => {
      try {
        const resp = await getEditedDoc(experimentId);
        if (cancelled) return;
        editor.commands.setContent(resp.doc as JSONContent, false);
        versionRef.current = resp.version;
        onEditedDocBehindChange?.(resp.edited_doc_behind_regeneration);
        // Persisted-on-load shows "Saved" with no timestamp (the endpoint
        // doesn't return edited_at). Generated stays idle until first edit.
        setLastSavedAt(null);
        setStatus(resp.source === "persisted" ? "saved" : "idle");
        setLoading(false);
      } catch {
        if (cancelled) return;
        setLoadError("Could not load the report editor.");
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [editor, experimentId, onEditedDocBehindChange, reloadKey]);

  useEffect(() => {
    if (!editor) return;
    const handler = () => {
      setStatus("unsaved");
      scheduleSave();
    };
    editor.on("update", handler);
    return () => {
      editor.off("update", handler);
    };
  }, [editor, scheduleSave]);

  useEffect(() => {
    if (!editor || !onSelectionChange) return;
    const handler = () => {
      const { from, to } = editor.state.selection;
      if (from === to) {
        onSelectionChange(null);
        return;
      }
      const text = editor.state.doc.textBetween(from, to, "\n", " ").trim();
      if (!text) {
        onSelectionChange(null);
        return;
      }
      onSelectionChange({ text, question_id: resolveQuestionId(editor, from) });
    };
    editor.on("selectionUpdate", handler);
    return () => {
      editor.off("selectionUpdate", handler);
    };
  }, [editor, onSelectionChange]);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      focusReference: (anchor: RefCitation) => {
        if (!editor || editor.isDestroyed) return;
        const range = findRefRange(editor, anchor);
        if (!range) return; // silent no-op when the anchor isn't in the doc

        editor.view.dispatch(editor.state.tr.setMeta(refHighlightKey, range));
        const { node } = editor.view.domAtPos(range.from);
        const el =
          node instanceof HTMLElement ? node : node.parentElement ?? null;
        el?.scrollIntoView({ behavior: "smooth", block: "center" });

        window.setTimeout(() => {
          if (!editor.isDestroyed) {
            editor.view.dispatch(
              editor.view.state.tr.setMeta(refHighlightKey, { clear: true }),
            );
          }
        }, REF_FLASH_MS);
      },
    }),
    [editor],
  );

  if (loadError) {
    return (
      <div className="border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm">
        <p className="font-mono text-mono-sm uppercase text-status-critical">
          {loadError}
        </p>
        <button
          type="button"
          onClick={() => setReloadKey((k) => k + 1)}
          className="mt-3 inline-flex items-center gap-1.5 border-2 border-border-master bg-surface-card px-3 py-1.5 font-mono text-mono-sm uppercase text-ink-primary transition-shadow hover:shadow-brutal-sm"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      </div>
    );
  }

  if (loading) {
    return <div className="fv-skeleton h-[380px] w-full" />;
  }

  return (
    <div className="relative">
      <div className="sticky top-0 z-10">
        <EvidenceEditorToolbar
          editor={editor}
          status={status}
          lastSavedAt={lastSavedAt}
        />
      </div>

      <div className="mt-2 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
});
