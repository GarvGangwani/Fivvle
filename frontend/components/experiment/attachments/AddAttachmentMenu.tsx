"use client";

import { useRef, useState } from "react";
import { createAttachment } from "@/lib/experiment-api";
import { useAttachments } from "../hooks/useAttachments";

function isValidUrl(s: string): boolean {
  try {
    const url = new URL(s.trim());
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

type Props = {
  experimentId: string;
  onAdd: () => void;
  onClose: () => void;
};

export function AddAttachmentMenu({ experimentId, onAdd, onClose }: Props) {
  const [mode, setMode] = useState<"menu" | "link">("menu");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkTitle, setLinkTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { upload } = useAttachments(experimentId);

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await upload(file);
      onAdd();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  const handleLinkSubmit = async () => {
    if (!isValidUrl(linkUrl) || !linkTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createAttachment(experimentId, {
        attachment_type: "link",
        title: linkTitle.trim(),
        file_url: linkUrl.trim(),
      });
      onAdd();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add link");
    } finally {
      setBusy(false);
    }
  };

  if (mode === "menu") {
    return (
      <div className="absolute right-0 top-full mt-1 w-56 rounded-md bg-surface-card border-2 border-border-master shadow-brutal-md z-50">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
          className="w-full text-left px-4 py-3 font-body text-body-md hover:bg-accent-muted border-b-2 border-border-master flex items-center gap-2 disabled:opacity-50"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
            upload_file
          </span>
          {busy ? "Uploading…" : "Upload file"}
        </button>
        <button
          type="button"
          onClick={() => setMode("link")}
          className="w-full text-left px-4 py-3 font-body text-body-md hover:bg-accent-muted flex items-center gap-2"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
            link
          </span>
          Add link
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,application/pdf,text/markdown,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(e) => void handleFileSelected(e)}
          className="hidden"
        />
        {error ? (
          <p className="px-4 py-2 font-body text-body-sm text-status-critical border-t-2 border-border-master">
            {error}
          </p>
        ) : null}
        <button
          type="button"
          onClick={onClose}
          className="sr-only"
          aria-label="Close menu"
        />
      </div>
    );
  }

  return (
    <div className="absolute right-0 top-full mt-1 w-80 rounded-md bg-surface-card border-2 border-border-master shadow-brutal-md p-4 z-50 nodrag">
      <label className="font-label-md text-label-md uppercase block mb-1">
        TITLE
      </label>
      <input
        type="text"
        value={linkTitle}
        onChange={(e) => setLinkTitle(e.target.value)}
        placeholder="e.g. Competitor pricing page"
        className="w-full rounded-md border-2 border-border-master bg-surface-card px-3 py-2 mb-3 font-body text-body-sm focus:shadow-brutal-primary focus:outline-none"
        autoFocus
      />
      <label className="font-label-md text-label-md uppercase block mb-1">
        URL
      </label>
      <input
        type="url"
        value={linkUrl}
        onChange={(e) => setLinkUrl(e.target.value)}
        placeholder="https://..."
        className="w-full rounded-md border-2 border-border-master bg-surface-card px-3 py-2 mb-3 font-body text-body-sm focus:shadow-brutal-primary focus:outline-none"
      />
      {error ? (
        <p className="mb-2 font-body text-body-sm text-status-critical">{error}</p>
      ) : null}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode("menu")}
          className="flex-1 rounded-sm border-2 border-border-master bg-surface-card px-3 py-2 font-label-md text-label-md uppercase shadow-brutal-sm hover:shadow-brutal-md transition-all"
        >
          BACK
        </button>
        <button
          type="button"
          onClick={() => void handleLinkSubmit()}
          disabled={!isValidUrl(linkUrl) || !linkTitle.trim() || busy}
          className="flex-1 rounded-sm bg-accent text-ink-inverse px-3 py-2 border-2 border-border-master font-label-md text-label-md uppercase shadow-brutal-sm hover:shadow-brutal-md disabled:opacity-50 transition-all"
        >
          {busy ? "ADDING…" : "ADD LINK"}
        </button>
      </div>
    </div>
  );
}
