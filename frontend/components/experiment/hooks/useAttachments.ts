"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createAttachment,
  deleteAttachment,
  listAttachments,
  patchAttachment,
  putAttachmentBytes,
  requestAttachmentUploadUrl,
} from "@/lib/experiment-api";
import type { AttachmentType, ExperimentAttachment } from "@/lib/types";

function mimeToAttachmentType(mime: string): AttachmentType {
  if (mime.startsWith("image/")) return "image";
  if (mime === "application/pdf") return "pdf";
  if (mime === "text/markdown") return "markdown";
  return "document";
}

export function useAttachments(experimentId: string) {
  const [items, setItems] = useState<ExperimentAttachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const refetch = useCallback(async () => {
    const rows = await listAttachments(experimentId);
    setItems(rows);
  }, [experimentId]);

  useEffect(() => {
    let cancelled = false;
    void listAttachments(experimentId)
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const upload = useCallback(
    async (file: File) => {
      setUploading(true);
      try {
        const signed = await requestAttachmentUploadUrl(experimentId, {
          filename: file.name,
          mime_type: file.type || "application/octet-stream",
          size_bytes: file.size,
        });
        await putAttachmentBytes(signed.upload_url, file);
        const row = await createAttachment(experimentId, {
          attachment_type: mimeToAttachmentType(file.type),
          title: file.name,
          file_url: signed.file_url,
          file_mime: file.type || null,
          file_size_bytes: file.size,
        });
        setItems((prev) => [row, ...prev]);
        return row;
      } finally {
        setUploading(false);
      }
    },
    [experimentId],
  );

  const pasteText = useCallback(
    async (title: string, content: string, asMarkdown = false) => {
      const row = await createAttachment(experimentId, {
        attachment_type: asMarkdown ? "markdown" : "pasted_text",
        title,
        content_text: content,
      });
      setItems((prev) => [row, ...prev]);
      return row;
    },
    [experimentId],
  );

  const remove = useCallback(
    async (id: string) => {
      await deleteAttachment(experimentId, id);
      setItems((prev) => prev.filter((row) => row.id !== id));
    },
    [experimentId],
  );

  const rename = useCallback(
    async (id: string, title: string) => {
      const row = await patchAttachment(experimentId, id, { title });
      setItems((prev) => prev.map((p) => (p.id === id ? row : p)));
      return row;
    },
    [experimentId],
  );

  return {
    items,
    loading,
    uploading,
    refetch,
    upload,
    pasteText,
    remove,
    rename,
  };
}
