"use client";

import { useCallback, useEffect, useState } from "react";
import {
  chatTurn,
  getExperimentChatMessages,
  uploadChatAttachments,
} from "@/lib/api";
import type { ChatHistoryMessage } from "@/lib/types";
import type { AttachmentDraft } from "./RefineChatInput";
import type { RefineChatMessageModel } from "./RefineChatMessage";
import type { RefineMessageAttachment } from "./MessageAttachments";

/**
 * Isolated Refine chat state. Reuses existing API helpers from `@/lib/api`:
 * - getExperimentChatMessages
 * - uploadChatAttachments
 * - chatTurn
 *
 * NOTE: POST /chat/turn returns a single JSON ChatTurnResponse — it does not
 * stream SSE. We show an is_streaming placeholder while awaiting the response,
 * then replace it with the full assistant_message.
 */

function mapHistoryMessage(msg: ChatHistoryMessage): RefineChatMessageModel {
  return {
    id: msg.id,
    role: msg.role === "assistant" ? "assistant" : "user",
    content: msg.content,
    attachments: [],
    created_at: msg.created_at,
    is_streaming: false,
  };
}

export function useRefineChat(experimentId: string) {
  const [messages, setMessages] = useState<RefineChatMessageModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const chatData = await getExperimentChatMessages(experimentId);
        if (cancelled) return;
        setThreadId(chatData.thread_id);
        setMessages(chatData.messages.map(mapHistoryMessage));
      } catch {
        if (!cancelled) {
          setMessages([]);
          setError("Could not load conversation.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const send = useCallback(
    async (text: string, attachments: AttachmentDraft[]) => {
      const clean = text.trim();
      if (!clean && attachments.length === 0) return;

      setSending(true);
      setError(null);

      const localAttachments: RefineMessageAttachment[] = attachments.map(
        (item) => ({
          id: item.id,
          filename: item.file.name,
          content_kind: item.file.type || undefined,
          previewUrl: item.previewUrl,
        }),
      );

      const optimisticUserId = `temp-user-${Date.now()}`;
      const assistantMsgId = `temp-assistant-${Date.now()}`;
      const now = new Date().toISOString();

      setMessages((prev) => [
        ...prev,
        {
          id: optimisticUserId,
          role: "user",
          content: clean || "Shared attachments",
          attachments: localAttachments,
          created_at: now,
        },
        {
          id: assistantMsgId,
          role: "assistant",
          content: "",
          attachments: [],
          created_at: now,
          is_streaming: true,
        },
      ]);

      try {
        let attachmentIds: string[] = [];
        if (attachments.length > 0) {
          const uploaded = await uploadChatAttachments(
            attachments.map((item) => item.file),
          );
          attachmentIds = uploaded.map((item) => item.id);
        }

        const response = await chatTurn({
          message: clean,
          deep_research: false,
          thread_id: threadId,
          experiment_id: experimentId,
          attachment_ids: attachmentIds,
        });

        setThreadId(response.thread_id);

        // Reload authoritative history so IDs / turn_kind match the server.
        const chatData = await getExperimentChatMessages(experimentId);
        setThreadId(chatData.thread_id);
        const mapped = chatData.messages.map(mapHistoryMessage);

        // Preserve local attachment previews on the latest user message when
        // the API history does not include attachment metadata.
        if (localAttachments.length > 0 && mapped.length > 0) {
          for (let i = mapped.length - 1; i >= 0; i -= 1) {
            if (mapped[i].role === "user") {
              mapped[i] = {
                ...mapped[i],
                attachments: localAttachments,
              };
              break;
            }
          }
        }

        setMessages(mapped);
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: "Something went wrong. Please try again.",
                  is_streaming: false,
                  error: true,
                }
              : m,
          ),
        );
        setError("Send failed.");
      } finally {
        setSending(false);
      }
    },
    [experimentId, threadId],
  );

  return { messages, loading, sending, send, error, threadId };
}
