"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2 } from "lucide-react";
import { chatTurn, ApiError } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
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
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const messageIdCounter = useRef(0);

  const nextMessageId = useCallback(() => {
    messageIdCounter.current += 1;
    return `local-${messageIdCounter.current}`;
  }, []);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(text: string) {
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
        deep_research: true,
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

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col bg-[var(--fv-bg)]">
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center py-12 text-center">
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

          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              timestamp={msg.timestamp}
            />
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="fv-msg-ai flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-[var(--fv-accent)]" />
                <span className="text-sm text-[var(--fv-text-muted)]">Thinking…</span>
              </div>
            </div>
          )}

          {researchStarted && experimentId && (
            <div className="fv-card border-[rgba(6,182,212,0.3)] bg-[var(--fv-accent-muted)] px-4 py-4">
              <p className="text-sm font-medium text-[var(--fv-accent)]">
                Research has started
              </p>
              <p className="mt-1 text-sm text-[var(--fv-text-soft)]">
                Your market research is running in the background. This
                typically takes 2–4 minutes.
              </p>
              <Link
                href={`/experiment/${experimentId}`}
                className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
              >
                View research progress
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}

          <div ref={scrollAnchorRef} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <ChatInput
          onSend={handleSend}
          disabled={loading || researchStarted}
          placeholder={
            messages.length === 0
              ? "Describe your startup idea…"
              : "Continue the conversation…"
          }
        />
      </div>
    </div>
  );
}
