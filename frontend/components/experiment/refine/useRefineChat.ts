"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  chatTurn,
  editChatMessage,
  generateRefinerOpener,
  getExperimentChatMessages,
  getMessageSiblings,
  retryRefineAssistantMessage,
  setActiveBranch,
  uploadChatAttachments,
} from "@/lib/api";
import type { ChatHistoryMessage, ClarifyingQuestion } from "@/lib/types";
import type { AttachmentDraft } from "./RefineChatInput";
import type { RefineChatMessageModel } from "./RefineChatMessage";
import type { RefineMessageAttachment } from "./MessageAttachments";
import type { MCQAnswer } from "./RefineMCQPopup";

export type MCQItem = {
  question: string;
  options: string[];
  fromMessageId: string;
};

export type McqSendMeta = {
  selectedOptionIndices: number[];
  customAddedText: string | null;
  answeredQuestionFromMessageId: string;
};

function mapHistoryMessage(msg: ChatHistoryMessage): RefineChatMessageModel {
  return {
    id: msg.id,
    role: msg.role === "assistant" ? "assistant" : "user",
    content: msg.content,
    attachments: [],
    created_at: msg.created_at,
    is_streaming: false,
    clarifying_questions: msg.clarifying_questions ?? undefined,
    metadata: msg.metadata ?? undefined,
    parent_message_id: msg.parent_message_id ?? null,
    sibling_index: msg.sibling_index ?? 0,
    sibling_count: msg.sibling_count ?? 1,
  };
}

function pickActiveMCQ(
  questions: ClarifyingQuestion[] | undefined | null,
  fromMessageId: string,
): MCQItem | null {
  if (!questions?.length) return null;
  const first = questions.find((q) => q.options.length >= 2);
  if (!first) return null;
  return {
    question: first.question,
    options: first.options,
    fromMessageId,
  };
}

function restoreMcqFromMessages(
  messages: RefineChatMessageModel[],
): MCQItem | null {
  if (messages.length === 0) return null;
  const latest = messages[messages.length - 1];
  if (latest.role !== "assistant") return null;
  return pickActiveMCQ(latest.clarifying_questions, latest.id);
}

type Options = {
  onTurnComplete?: () => void | Promise<void>;
  enableOpener?: boolean;
};

export function useRefineChat(experimentId: string, options: Options = {}) {
  const { onTurnComplete, enableOpener = true } = options;
  const [messages, setMessages] = useState<RefineChatMessageModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingOpener, setGeneratingOpener] = useState(false);
  const [sending, setSending] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [activeMCQ, setActiveMCQ] = useState<MCQItem | null>(null);
  const [dismissedMCQMessageIds, setDismissedMCQMessageIds] = useState<
    Set<string>
  >(new Set());
  const [refinementCount, setRefinementCount] = useState(0);
  const [navigatingMessageId, setNavigatingMessageId] = useState<string | null>(
    null,
  );

  const reload = useCallback(() => {
    setReloadToken((n) => n + 1);
  }, []);

  const dismissMCQ = useCallback(() => {
    setActiveMCQ((current) => {
      if (current) {
        setDismissedMCQMessageIds((prev) => new Set(prev).add(current.fromMessageId));
      }
      return null;
    });
  }, []);

  const reopenMCQ = useCallback(
    (messageId: string) => {
      const message = messages.find((m) => m.id === messageId);
      if (!message || message.role !== "assistant") return;
      const mcq = pickActiveMCQ(message.clarifying_questions, messageId);
      if (!mcq) return;
      setActiveMCQ(mcq);
      setDismissedMCQMessageIds((prev) => {
        const next = new Set(prev);
        next.delete(messageId);
        return next;
      });
    },
    [messages],
  );

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setGeneratingOpener(false);
      try {
        const chatData = await getExperimentChatMessages(experimentId);
        if (cancelled) return;
        setThreadId(chatData.thread_id);
        let mapped = chatData.messages.map(mapHistoryMessage);
        setMessages(mapped);
        setActiveMCQ(restoreMcqFromMessages(mapped));
        setLoading(false);

        if (enableOpener && mapped.length === 0) {
          setGeneratingOpener(true);
          try {
            await generateRefinerOpener(experimentId);
            if (cancelled) return;
            const refreshed = await getExperimentChatMessages(experimentId);
            if (cancelled) return;
            setThreadId(refreshed.thread_id);
            mapped = refreshed.messages.map(mapHistoryMessage);
            setMessages(mapped);
            setActiveMCQ(restoreMcqFromMessages(mapped));
          } catch (err) {
            if (!(err instanceof ApiError && err.status === 400)) {
              console.error("Opener generation failed:", err);
            }
          } finally {
            if (!cancelled) setGeneratingOpener(false);
          }
        }
      } catch {
        if (!cancelled) {
          setMessages([]);
          setActiveMCQ(null);
          setError("Could not load conversation.");
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [experimentId, reloadToken, enableOpener]);

  const send = useCallback(
    async (
      text: string,
      attachments: AttachmentDraft[],
      mcqMeta?: McqSendMeta,
    ) => {
      const clean = text.trim();
      if (!clean && attachments.length === 0) return;

      setActiveMCQ(null);
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
          metadata: mcqMeta
            ? {
                selected_option_indices: mcqMeta.selectedOptionIndices,
                custom_added_text: mcqMeta.customAddedText,
                answered_question_from_message_id:
                  mcqMeta.answeredQuestionFromMessageId,
              }
            : undefined,
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
          deep_research: true,
          thread_id: threadId,
          experiment_id: experimentId,
          attachment_ids: attachmentIds,
          selected_option_indices: mcqMeta?.selectedOptionIndices ?? null,
          custom_added_text: mcqMeta?.customAddedText ?? null,
          answered_question_from_message_id:
            mcqMeta?.answeredQuestionFromMessageId ?? null,
        });

        setThreadId(response.thread_id);

        if (
          typeof response.refinement_count === "number" &&
          response.refinement_count >= 0
        ) {
          setRefinementCount(response.refinement_count);
        }

        const chatData = await getExperimentChatMessages(experimentId);
        setThreadId(chatData.thread_id);
        const mapped = chatData.messages.map(mapHistoryMessage);

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
        await onTurnComplete?.();

        const mcq = pickActiveMCQ(
          response.clarifying_questions,
          response.message_id,
        );
        setActiveMCQ(mcq);
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
    [experimentId, threadId, onTurnComplete],
  );

  const answerMCQ = useCallback(
    async (answer: MCQAnswer) => {
      const fromId = activeMCQ?.fromMessageId;
      setActiveMCQ(null);
      if (fromId) {
        setDismissedMCQMessageIds((prev) => {
          const next = new Set(prev);
          next.delete(fromId);
          return next;
        });
      }
      await send(answer.combinedText, [], {
        selectedOptionIndices: answer.selectedIndices,
        customAddedText: answer.customAddedText,
        answeredQuestionFromMessageId: fromId ?? "",
      });
    },
    [send, activeMCQ],
  );

  const editMessage = useCallback(
    async (messageId: string, newContent: string) => {
      if (!threadId) return;
      setSending(true);
      setError(null);
      try {
        await editChatMessage(threadId, messageId, newContent);
        const chatData = await getExperimentChatMessages(experimentId);
        setThreadId(chatData.thread_id);
        const mapped = chatData.messages.map(mapHistoryMessage);
        setMessages(mapped);
        setActiveMCQ(restoreMcqFromMessages(mapped));
        await onTurnComplete?.();
      } catch {
        setError("Edit failed.");
      } finally {
        setSending(false);
      }
    },
    [threadId, experimentId, onTurnComplete],
  );

  const retryMessage = useCallback(
    async (messageId: string) => {
      setSending(true);
      setError(null);
      setActiveMCQ(null);
      try {
        const response = await retryRefineAssistantMessage(
          experimentId,
          messageId,
        );
        if (
          typeof response.refinement_count === "number" &&
          response.refinement_count >= 0
        ) {
          setRefinementCount(response.refinement_count);
        }
        const chatData = await getExperimentChatMessages(experimentId);
        setThreadId(chatData.thread_id);
        const mapped = chatData.messages.map(mapHistoryMessage);
        setMessages(mapped);
        const mcq = pickActiveMCQ(
          response.clarifying_questions,
          response.message_id,
        );
        setActiveMCQ(mcq);
        await onTurnComplete?.();
      } catch {
        setError("Retry failed.");
      } finally {
        setSending(false);
      }
    },
    [experimentId, onTurnComplete],
  );

  const switchToBranch = useCallback(
    async (fromMessageId: string, direction: "prev" | "next") => {
      if (navigatingMessageId) return;
      setNavigatingMessageId(fromMessageId);
      setError(null);

      try {
        const siblings = await getMessageSiblings(experimentId, fromMessageId);
        const currentIdx = siblings.findIndex((s) => s.id === fromMessageId);
        if (currentIdx === -1) return;

        const targetIdx = direction === "next" ? currentIdx + 1 : currentIdx - 1;
        if (targetIdx < 0 || targetIdx >= siblings.length) return;

        const targetSiblingId = siblings[targetIdx].id;
        await setActiveBranch(experimentId, targetSiblingId);

        const chatData = await getExperimentChatMessages(experimentId);
        setThreadId(chatData.thread_id);
        const mapped = chatData.messages.map(mapHistoryMessage);
        setMessages(mapped);
        setDismissedMCQMessageIds(new Set());
        setActiveMCQ(restoreMcqFromMessages(mapped));
        await onTurnComplete?.();
      } catch (err) {
        console.error("Failed to switch branch:", err);
        setError("Could not switch branch.");
      } finally {
        setNavigatingMessageId(null);
      }
    },
    [experimentId, navigatingMessageId, onTurnComplete],
  );

  return {
    messages,
    loading,
    generatingOpener,
    sending,
    send,
    error,
    threadId,
    reload,
    activeMCQ,
    answerMCQ,
    dismissMCQ,
    reopenMCQ,
    dismissedMCQMessageIds,
    refinementCount,
    editMessage,
    retryMessage,
    switchToBranch,
    navigatingMessageId,
  };
}
