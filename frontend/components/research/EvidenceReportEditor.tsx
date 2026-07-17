"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  EditorContent,
  useEditor,
  type JSONContent,
} from "@tiptap/react";
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
import { FontSize } from "@/lib/tiptap-font-size";
import { useToast } from "@/components/ui/ToastProvider";
import { EvidenceEditorToolbar } from "@/components/research/EvidenceEditorToolbar";
import "./evidence-editor.css";

const AUTOSAVE_DEBOUNCE_MS = 1200;

type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";

interface EvidenceReportEditorProps {
  experimentId: string;
  /** Lifts staleness up so the panel can render the banner above the header. */
  onStaleChange?: (stale: boolean) => void;
}

export function EvidenceReportEditor({
  experimentId,
  onStaleChange,
}: EvidenceReportEditorProps) {
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
      onStaleChange?.(resp.is_stale_since_regeneration);
      setLastSavedAt(new Date());
      setStatus("saved");
    } catch (err) {
      if (err instanceof EditedDocVersionConflict) {
        try {
          const fresh = await getEditedDoc(experimentId);
          editor.commands.setContent(fresh.doc as JSONContent, false);
          versionRef.current = fresh.version;
          onStaleChange?.(fresh.is_stale_since_regeneration);
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
  }, [editor, experimentId, onStaleChange, toast]);

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
        onStaleChange?.(resp.is_stale_since_regeneration);
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
  }, [editor, experimentId, onStaleChange, reloadKey]);

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
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

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

  const statusText =
    status === "saving"
      ? "Saving…"
      : status === "unsaved"
        ? "Unsaved changes"
        : status === "error"
          ? "Save failed — will retry on next edit"
          : status === "saved"
            ? lastSavedAt
              ? `Saved • ${lastSavedAt.toLocaleTimeString([], {
                  hour: "numeric",
                  minute: "2-digit",
                })}`
              : "Saved"
            : "";

  return (
    <div className="relative">
      <div className="sticky top-0 z-10">
        <EvidenceEditorToolbar editor={editor} />
      </div>

      <div
        aria-live="polite"
        className={`pointer-events-none absolute right-2 top-14 z-20 font-mono text-mono-sm uppercase ${
          status === "error" ? "text-status-critical" : "text-ink-tertiary"
        }`}
      >
        {statusText}
      </div>

      <div className="mt-2 border-2 border-border-master bg-surface-card p-4 shadow-brutal-sm">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
