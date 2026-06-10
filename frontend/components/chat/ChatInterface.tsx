"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { chatTurn, getExperiment, ApiError } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import { Eye } from "lucide-react";
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

const STARTER_PROMPTS = [
  "A tool that helps remote teams run async standups",
  "An app that matches dog owners for local group walks",
  "A marketplace for freelance CFOs serving startups",
  "A browser extension that summarizes Slack threads",
] as const;

const SCROLL_NEAR_BOTTOM_THRESHOLD_PX = 100;

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
  const [hasValidationReport, setHasValidationReport] = useState(false);
  const [prefillText, setPrefillText] = useState<string | null>(null);
  const [prefillNonce, setPrefillNonce] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const forceScrollRef = useRef(false);
  const messageIdCounter = useRef(0);

  const nextMessageId = useCallback(() => {
    messageIdCounter.current += 1;
    return `local-${messageIdCounter.current}`;
  }, []);

  const updateNearBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      isNearBottomRef.current = true;
      return;
    }
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    isNearBottomRef.current =
      distanceFromBottom <= SCROLL_NEAR_BOTTOM_THRESHOLD_PX;
  }, []);

  const handleScroll = useCallback(() => {
    updateNearBottom();
  }, [updateNearBottom]);

  useEffect(() => {
    if (forceScrollRef.current || isNearBottomRef.current) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
      forceScrollRef.current = false;
    }
  }, [messages, loading, researchStarted, hasValidationReport]);

  useEffect(() => {
    if (!experimentId || !researchStarted) {
      setHasValidationReport(false);
      return;
    }

    let cancelled = false;

    async function loadExperiment() {
      if (!experimentId) return;
      try {
        const data = await getExperiment(experimentId);
        if (!cancelled) {
          setHasValidationReport(data.validation_report != null);
        }
      } catch {
        // Ignore — progress polling handles transient errors elsewhere
      }
    }

    void loadExperiment();
    const intervalId = setInterval(loadExperiment, 3000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [experimentId, researchStarted]);

  function handleStarterChipClick(text: string) {
    setPrefillText(text);
    setPrefillNonce((n) => n + 1);
  }

  async function handleSend(text: string, deepResearch: boolean) {
    forceScrollRef.current = true;
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
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-6 py-8 sm:px-12"
        >
          <div className="mx-auto w-full">
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
                <div className="mt-6 flex max-w-lg flex-wrap justify-center gap-2">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleStarterChipClick(prompt)}
                      className="cursor-pointer rounded-full border border-white/[0.1] bg-white/[0.03] px-4 py-2 text-[13px] text-fv-text-soft transition-all duration-200 hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
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
              <div className="fv-msg-enter border-b border-[var(--fv-border)] py-6">
                <div className="mx-auto max-w-[680px]">
                  <div className="flex items-start gap-3">
                    <div
                      className="fv-f-logo"
                      style={{ width: 24, height: 24, fontSize: 12 }}
                      aria-hidden
                    >
                      F
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
                        Fivvle
                      </span>
                      <div className="flex items-center gap-1.5 py-1">
                        {[0, 150, 300].map((delay) => (
                          <span
                            key={delay}
                            className="h-2 w-2 animate-pulse rounded-full bg-[var(--fv-text-dim)]"
                            style={{ animationDelay: `${delay}ms` }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {researchStarted && experimentId && (
              <InlineResearchProgress experimentId={experimentId} />
            )}

            {hasValidationReport && experimentId && (
              <div className="border-b border-[var(--fv-border)] py-6">
                <div className="mx-auto max-w-[680px]">
                  <button
                    type="button"
                    onClick={() => setReportOpen(true)}
                    className="view-report-btn"
                  >
                    <Eye className="h-4 w-4" />
                    View Validation Report
                  </button>
                </div>
              </div>
            )}

            <div ref={scrollAnchorRef} />
          </div>
        </div>

        <ChatInput
          onSend={handleSend}
          disabled={chatDisabled}
          deepResearchLocked={researchStarted}
          prefillText={prefillText}
          prefillNonce={prefillNonce}
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
