"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { chatTurn, ApiError } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import { InlineResearchProgress } from "@/components/research/InlineResearchProgress";
import { ValidationReportPanel } from "@/components/research/ValidationReportPanel";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

function isResearchUnderway(
  pipelineDispatched: boolean,
  experimentStatus: string | null,
): boolean {
  if (pipelineDispatched) return true;
  return (
    experimentStatus !== null &&
    RESEARCH_ACTIVE_STATUSES.has(experimentStatus)
  );
}

function apiErrorMessage(err: ApiError): string {
  if (err.status === 429) {
    const retry = err.retryAfterSeconds;
    return retry
      ? `Too many requests. Try again in ${retry} seconds.`
      : "Too many requests. Please wait a moment and try again.";
  }
  if (err.status === 409) {
    return "This experiment is no longer in refinement. Start a new idea from the dashboard.";
  }
  if (err.status === 404) {
    if (process.env.NODE_ENV === "development") {
      return "Chat is not available. Set AUTO_FIRE_CHAT_ENABLED=on in backend/.env and restart the API.";
    }
    return "Chat is not available right now. Please try again later.";
  }
  return "Something went wrong. Please try again.";
}

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [experimentId, setExperimentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [researchStarted, setResearchStarted] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const messageIdCounter = useRef(0);

  const nextMessageId = useCallback(() => {
    messageIdCounter.current += 1;
    return `local-${messageIdCounter.current}`;
  }, []);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, researchStarted]);

  async function handleSend(text: string, deepResearch: boolean) {
    const userMessage: ChatMessageType = {
      id: nextMessageId(),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatTurn({
        message: text,
        deep_research: deepResearch,
        thread_id: threadId,
        experiment_id: experimentId,
        idempotency_key: crypto.randomUUID(),
      });

      setThreadId(response.thread_id);
      if (response.experiment_id) {
        setExperimentId(response.experiment_id);
      }

      const assistantMessage: ChatMessageType = {
        id: response.message_id,
        role: "assistant",
        content: response.assistant_message,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (
        isResearchUnderway(
          response.pipeline_dispatched,
          response.experiment_status,
        )
      ) {
        setResearchStarted(true);
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? apiErrorMessage(err)
          : "Something went wrong. Please try again.";

      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId(),
          role: "assistant",
          content: message,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const chatDisabled = loading || researchStarted;

  return (
    <>
      <div className="flex h-full min-h-0 flex-1 flex-col bg-[var(--fv-bg)]">
        <div className="flex-1 overflow-y-auto px-6 py-8 sm:px-12">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center py-16 text-center">
                <div
                  className="fv-f-logo mb-4"
                  style={{ width: 40, height: 40, fontSize: 20 }}
                >
                  F
                </div>
                <h2 className="text-lg font-semibold text-[var(--fv-text)]">
                  What&apos;s your idea?
                </h2>
                <p className="mt-2 max-w-md text-sm text-[var(--fv-text-muted)]">
                  Describe the problem you want to solve, who it&apos;s for, and
                  your proposed solution. Fivvle will refine it through a short
                  conversation, then kick off market research.
                </p>
              </div>
            )}

            {messages.map((msg, index) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                showRefining={
                  msg.role === "assistant" &&
                  !researchStarted &&
                  index === messages.length - 1 &&
                  !loading
                }
              />
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="w-full max-w-[80%]">
                  <div className="mb-1.5 flex items-center gap-2">
                    <div
                      className="fv-f-logo"
                      style={{ width: 22, height: 22, fontSize: 11 }}
                    >
                      F
                    </div>
                    <span className="text-[12px] font-medium text-fv-text-dim">
                      Fivvle
                    </span>
                  </div>
                  <div className="fv-msg-ai flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-[var(--fv-accent)]" />
                    <span className="text-sm text-[var(--fv-text-muted)]">
                      Thinking…
                    </span>
                  </div>
                </div>
              </div>
            )}

            {researchStarted && experimentId && (
              <InlineResearchProgress
                experimentId={experimentId}
                onViewReport={() => setReportOpen(true)}
              />
            )}

            <div ref={scrollAnchorRef} />
          </div>
        </div>

        <ChatInput
          onSend={handleSend}
          disabled={chatDisabled}
          deepResearchLocked={researchStarted}
          placeholder={
            messages.length === 0
              ? "Describe your idea..."
              : "Continue the conversation…"
          }
        />
      </div>

      {experimentId && (
        <ValidationReportPanel
          experimentId={experimentId}
          open={reportOpen}
          onClose={() => setReportOpen(false)}
        />
      )}
    </>
  );
}
