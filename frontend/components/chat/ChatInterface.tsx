"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  chatTurn,
  confirmExperiment,
  editChatMessage,
  getExperiment,
  getExperimentChatMessages,
  ApiError,
} from "@/lib/api";
import type { ChatMessage as ChatMessageType, ChatTurnKind, ClarifyingQuestion, ClarifyingQuestionAnswer } from "@/lib/types";
import { FileText } from "lucide-react";
import { InlineResearchProgress } from "@/components/research/InlineResearchProgress";
import { ReportCanvas } from "@/components/research/ReportCanvas";
import { ClarifyingQuestionBlock } from "@/components/refinement/ClarifyingQuestionBlock";
import { ClarifyingQuestionsLoading } from "@/components/refinement/ClarifyingQuestionsLoading";
import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
import { PressureTestSection } from "@/components/refinement/PressureTestSection";
import {
  findPendingQuestionBlock,
  formatClarifyingAnswers,
} from "@/lib/clarifying-questions";
import {
  collectPastClarifyingTurns,
  collectSourcedClarityBlocks,
  parseClarifyingAnswerContent,
} from "@/lib/refinement-thread";
import { ChatInput } from "./ChatInput";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { shouldShowValidationResearchPrompt } from "@/lib/validation-flow";
import { useValidationPaywallGate } from "@/components/wallet/useValidationPaywallGate";
import { ValidationResearchPrompt } from "@/components/wallet/ValidationResearchPrompt";
import { VALIDATION_PAYWALL_CREDITS } from "@/lib/wallet-paywall";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import { useWallet } from "@/lib/wallet-context";

const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

const DEEP_RESEARCH_LOCKED_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
  "RESEARCH_READY",
  "RESEARCH_FAILED",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "COMPLETED",
  "ARCHIVED",
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

function isDeepResearchLocked(status: string | null): boolean {
  return status !== null && DEEP_RESEARCH_LOCKED_STATUSES.has(status);
}

function isResearchTriggeredStatus(status: string | null): boolean {
  if (status === null) return false;
  return isDeepResearchLocked(status);
}

const STARTER_PROMPTS = [
  "A tool that helps remote teams run async standups",
  "An app that matches dog owners for local group walks",
  "A marketplace for freelance CFOs serving startups",
  "A browser extension that summarizes Slack threads",
] as const;

const SCROLL_NEAR_BOTTOM_THRESHOLD_PX = 100;
const CHAT_TURN_TIMEOUT_MS = 120_000;

function mapApiMessages(
  messages: {
    id: string;
    role: ChatMessageType["role"];
    content: string;
    created_at: string;
    turn_kind?: ChatTurnKind | null;
    clarifying_questions?: ClarifyingQuestion[] | null;
  }[],
): ChatMessageType[] {
  return messages.map((msg) => ({
    id: msg.id,
    role: msg.role,
    content: msg.content,
    timestamp: msg.created_at,
    turnKind: msg.turn_kind ?? undefined,
    clarifyingQuestions: msg.clarifying_questions ?? undefined,
  }));
}

function isPersistedMessageId(id: string): boolean {
  return !id.startsWith("local-");
}

function formatReportDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(iso));
}

function apiErrorMessage(err: ApiError): string {
  if (err.status === 429) {
    const retry = err.retryAfterSeconds;
    return retry
      ? `Too many requests. Try again in ${retry} seconds.`
      : "Too many requests. Please wait a moment and try again.";
  }
  if (err.status === 402) {
    return (
      readPaidActionError(err, {
        fallbackRequired: VALIDATION_PAYWALL_CREDITS,
        fallback:
          "Not enough credits to start validation. Open your wallet to buy more.",
      })
    );
  }
  if (err.status === 409) {
    return "This experiment is archived or unavailable for chat.";
  }
  if (err.status === 404) {
    if (process.env.NODE_ENV === "development") {
      return "Chat is not available. Set AUTO_FIRE_CHAT_ENABLED=shadow (or on) in backend/.env and restart the API.";
    }
    return "Chat is not available right now. Please try again later.";
  }
  if (err.status === 502) {
    return readPaidActionError(err);
  }
  return "Something went wrong. Please try again.";
}

export interface ChatInterfaceProps {
  experimentId?: string;
  onExperimentChange?: () => void;
  onRefinementFinalized?: (finalized: boolean) => void;
}

export function ChatInterface({
  experimentId,
  onExperimentChange,
  onRefinementFinalized,
}: ChatInterfaceProps = {}) {
  const router = useRouter();
  const { requestValidation, paywallModal } = useValidationPaywallGate();
  const { refresh: refreshWallet, applyWalletPatch } = useWallet();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [resolvedExperimentId, setResolvedExperimentId] = useState<string | null>(
    experimentId ?? null,
  );
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(Boolean(experimentId));
  const [researchStarted, setResearchStarted] = useState(false);
  const [canvasOpen, setCanvasOpen] = useState(false);
  const [hasValidationReport, setHasValidationReport] = useState(false);
  const [reportReadyAt, setReportReadyAt] = useState<string | null>(null);
  const [prefillText, setPrefillText] = useState<string | null>(null);
  const [prefillNonce, setPrefillNonce] = useState(0);
  const [projectName, setProjectName] = useState("");
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
    if (!experimentId) {
      setHistoryLoading(false);
      return;
    }

    let cancelled = false;

    async function loadExperimentChat() {
      setHistoryLoading(true);
      try {
        const [experiment, chatData] = await Promise.all([
          getExperiment(experimentId!),
          getExperimentChatMessages(experimentId!),
        ]);

        if (cancelled) return;

        setResolvedExperimentId(experimentId!);
        setExperimentStatus(experiment.status);
        if (experiment.name?.trim()) {
          setProjectName(experiment.name.trim());
        }
        const reportAvailable = experiment.validation_report != null;
        setHasValidationReport(reportAvailable);
        if (reportAvailable) {
          const lastMessage = chatData.messages.at(-1);
          setReportReadyAt(
            lastMessage?.created_at ?? new Date().toISOString(),
          );
        }

        if (isResearchTriggeredStatus(experiment.status)) {
          setResearchStarted(true);
        } else if (experiment.status === "REFINED") {
          setResearchStarted(false);
        }

        if (chatData.thread_id) {
          setThreadId(chatData.thread_id);
        }

        setMessages(mapApiMessages(chatData.messages));

        const finalized = chatData.messages.some(
          (m) => m.turn_kind === "refinement_finalize",
        );
        if (finalized) {
          onRefinementFinalized?.(true);
        }
      } catch {
        if (!cancelled) {
          setMessages([]);
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    }

    void loadExperimentChat();

    return () => {
      cancelled = true;
    };
  }, [experimentId, onRefinementFinalized]);

  useEffect(() => {
    const activeExperimentId = resolvedExperimentId;
    if (!activeExperimentId || !researchStarted) {
      if (!experimentId) {
        setHasValidationReport(false);
      }
      return;
    }

    let cancelled = false;

    async function loadExperiment() {
      if (!activeExperimentId) return;
      try {
        const data = await getExperiment(activeExperimentId);
        if (!cancelled) {
          setExperimentStatus(data.status);
          const reportAvailable = data.validation_report != null;
          if (reportAvailable) {
            setHasValidationReport(true);
            setReportReadyAt((prev) => prev ?? new Date().toISOString());
          } else {
            setHasValidationReport(false);
          }
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
  }, [resolvedExperimentId, researchStarted, experimentId]);

  function handleStarterChipClick(text: string) {
    setPrefillText(text);
    setPrefillNonce((n) => n + 1);
  }

  const refreshChatMessages = useCallback(async () => {
    const expId = resolvedExperimentId ?? experimentId;
    if (!expId) return;
    try {
      const chatData = await getExperimentChatMessages(expId);
      setMessages(mapApiMessages(chatData.messages));
      if (chatData.thread_id) {
        setThreadId(chatData.thread_id);
      }
    } catch {
      // Non-blocking — user can retry
    }
  }, [resolvedExperimentId, experimentId]);

  async function handleSend(
    text: string,
    deepResearch: boolean,
    attachments: Array<{ id: string; filename: string }> = [],
  ) {
    forceScrollRef.current = true;
    const attachmentLine =
      attachments.length > 0
        ? `\n\n📎 ${attachments.map((item) => item.filename).join(", ")}`
        : "";
    const userMessage: ChatMessageType = {
      id: nextMessageId(),
      role: "user",
      content: `${text || "Shared attachments"}${attachmentLine}`,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, CHAT_TURN_TIMEOUT_MS);

    try {
      const response = await chatTurn({
        message: text,
        deep_research: deepResearch,
        thread_id: threadId,
        experiment_id: resolvedExperimentId,
        idempotency_key: crypto.randomUUID(),
        name:
          !resolvedExperimentId && projectName.trim()
            ? projectName.trim()
            : undefined,
        attachment_ids: attachments.map((item) => item.id),
        signal: controller.signal,
      });

      const createdNewExperiment =
        !resolvedExperimentId && response.experiment_id != null;

      setThreadId(response.thread_id);
      if (response.experiment_id) {
        setResolvedExperimentId(response.experiment_id);
      }
      if (response.experiment_status) {
        setExperimentStatus(response.experiment_status);
      }

      if (deepResearch && response.experiment_id) {
        const chatData = await getExperimentChatMessages(response.experiment_id);
        setMessages(mapApiMessages(chatData.messages));
        if (chatData.thread_id) {
          setThreadId(chatData.thread_id);
        }
      } else {
        const assistantMessage: ChatMessageType = {
          id: response.message_id,
          role: "assistant",
          content: response.assistant_message,
          timestamp: new Date().toISOString(),
          turnKind: response.turn_kind,
          clarifyingQuestions: response.clarifying_questions,
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }

      if (
        response.turn_kind === "refinement_finalize" &&
        !response.pipeline_dispatched
      ) {
        setResearchStarted(false);
        setExperimentStatus(response.experiment_status ?? "REFINED");
      } else if (
        isResearchUnderway(
          response.pipeline_dispatched,
          response.experiment_status,
        )
      ) {
        setResearchStarted(true);
      }

      if (createdNewExperiment || response.turn_kind === "refinement_finalize") {
        notifyExperimentsChanged();
      }

      if (response.turn_kind === "refinement_finalize") {
        onRefinementFinalized?.(true);
      }

      if (createdNewExperiment && response.experiment_id && !experimentId) {
        router.replace(`/experiment/${response.experiment_id}`);
        return;
      }

      if (response.experiment_id && response.turn_kind === "refinement_finalize") {
        try {
          const exp = await getExperiment(response.experiment_id);
          if (exp.name?.trim()) {
            setProjectName(exp.name.trim());
          }
        } catch {
          // Non-blocking — sidebar still refreshes via event
        }
      }
    } catch (err) {
      const message = timedOut
        ? "This is taking longer than expected. Try refreshing — your answer may already be saved."
        : err instanceof ApiError
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

      if (timedOut) {
        void refreshChatMessages();
      }
    } finally {
      window.clearTimeout(timeoutId);
      setLoading(false);
    }
  }

  async function handleStartValidation() {
    const expId = resolvedExperimentId ?? experimentId;
    if (!expId) return;

    const runConfirm = async () => {
      setLoading(true);
      try {
        const result = await confirmExperiment(expId);
        await syncWalletAfterPaidAction(
          refreshWallet,
          applyWalletPatch,
          result.credits_balance,
        );
        setResearchStarted(true);
        setExperimentStatus("RESEARCHING");
        notifyExperimentsChanged();
        onExperimentChange?.();
      } catch (err) {
        if (err instanceof ApiError && err.status === 502) {
          await refreshWallet();
        }
        const message =
          err instanceof ApiError
            ? apiErrorMessage(err)
            : "Could not start validation. Please try again.";
        setMessages((prev) => [
          ...prev,
          {
            id: nextMessageId(),
            role: "assistant",
            content: message,
            timestamp: new Date().toISOString(),
          },
        ]);
        throw err;
      } finally {
        setLoading(false);
      }
    };

    requestValidation(async () => {
      await runConfirm();
    });
  }

  const handleEditMessageInternal = useCallback(
    async (
      messageId: string,
      newContent: string,
      options?: { rethrowOnly?: boolean },
    ) => {
      if (!threadId) {
        if (options?.rethrowOnly) {
          throw new Error("Chat thread not ready");
        }
        return;
      }

      const editIndex = messages.findIndex((msg) => msg.id === messageId);
      if (editIndex === -1) {
        if (options?.rethrowOnly) {
          throw new Error("Message not found");
        }
        return;
      }

      forceScrollRef.current = true;
      setMessages((prev) =>
        prev
          .slice(0, editIndex + 1)
          .map((msg, idx) =>
            idx === editIndex ? { ...msg, content: newContent } : msg,
          ),
      );
      setLoading(true);

      try {
        const response = await editChatMessage(threadId, messageId, newContent);

        setThreadId(response.thread_id);
        if (response.experiment_id) {
          setResolvedExperimentId(response.experiment_id);
        }
        if (response.experiment_status) {
          setExperimentStatus(response.experiment_status);
        }

        setMessages(mapApiMessages(response.messages));

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

        if (!options?.rethrowOnly) {
          setMessages((prev) => [
            ...prev,
            {
              id: nextMessageId(),
              role: "assistant",
              content: message,
              timestamp: new Date().toISOString(),
            },
          ]);
        }
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [threadId, messages, nextMessageId],
  );

  const handleEditMessage = useCallback(
    async (messageId: string, newContent: string) => {
      await handleEditMessageInternal(messageId, newContent);
    },
    [handleEditMessageInternal],
  );

  const chatDisabled =
    loading || historyLoading || experimentStatus === "ARCHIVED";
  const pendingQuestionBlock = useMemo(
    () => findPendingQuestionBlock(messages),
    [messages],
  );
  const firstUserMessageId = useMemo(
    () => messages.find((m) => m.role === "user")?.id,
    [messages],
  );
  const originalIdea = useMemo(
    () => messages.find((m) => m.role === "user")?.content,
    [messages],
  );
  const allClarityBlocks = useMemo(
    () => collectSourcedClarityBlocks(messages, firstUserMessageId ?? null),
    [messages, firstUserMessageId],
  );
  const pastClarifyingTurns = useMemo(
    () => collectPastClarifyingTurns(messages, firstUserMessageId ?? null),
    [messages, firstUserMessageId],
  );
  const handleEditPastClarifyingAnswer = useCallback(
    async (messageId: string, answer: ClarifyingQuestionAnswer) => {
      const turnIndex = pastClarifyingTurns.findIndex(
        (turn) => turn.answerMessageId === messageId,
      );
      const pastTurn =
        turnIndex >= 0 ? pastClarifyingTurns[turnIndex] : undefined;
      if (!pastTurn) return;

      let resolvedMessageId = messageId;
      let question = pastTurn.question;

      if (!isPersistedMessageId(messageId)) {
        const expId = resolvedExperimentId ?? experimentId;
        if (!expId) {
          throw new Error("Experiment not ready");
        }
        const chatData = await getExperimentChatMessages(expId);
        const freshMessages = mapApiMessages(chatData.messages);
        setMessages(freshMessages);
        if (chatData.thread_id) {
          setThreadId(chatData.thread_id);
        }
        const firstUserId =
          freshMessages.find((m) => m.role === "user")?.id ?? null;
        const freshPastTurns = collectPastClarifyingTurns(
          freshMessages,
          firstUserId,
        );
        const freshTurn =
          turnIndex >= 0 ? freshPastTurns[turnIndex] : undefined;
        if (!freshTurn || !isPersistedMessageId(freshTurn.answerMessageId)) {
          throw new Error("Could not resolve saved answer");
        }
        resolvedMessageId = freshTurn.answerMessageId;
        question = freshTurn.question;
      }

      const newContent = formatClarifyingAnswers([question], [answer]);
      await handleEditMessageInternal(resolvedMessageId, newContent, {
        rethrowOnly: true,
      });
    },
    [
      pastClarifyingTurns,
      resolvedExperimentId,
      experimentId,
      handleEditMessageInternal,
    ],
  );
  const clarityContentKey = useMemo(
    () =>
      messages
        .filter(
          (m) =>
            m.role === "user" &&
            m.id !== firstUserMessageId &&
            parseClarifyingAnswerContent(m.content),
        )
        .map((m) => m.content)
        .join("\n---\n"),
    [messages, firstUserMessageId],
  );
  const clarityMessageContentById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const msg of messages) {
      if (
        msg.role === "user" &&
        msg.id !== firstUserMessageId &&
        parseClarifyingAnswerContent(msg.content)
      ) {
        map[msg.id] = msg.content;
      }
    }
    return map;
  }, [messages, firstUserMessageId]);
  const hasRefinementFinalize = useMemo(
    () => messages.some((m) => m.turnKind === "refinement_finalize"),
    [messages],
  );

  useEffect(() => {
    onRefinementFinalized?.(hasRefinementFinalize);
  }, [hasRefinementFinalize, onRefinementFinalized]);
  const awaitingRefinementAfterUser = useMemo(() => {
    if (hasRefinementFinalize) return false;
    const last = messages[messages.length - 1];
    if (!last || last.role !== "user") return false;
    if (last.id === firstUserMessageId) {
      return allClarityBlocks.length === 0;
    }
    return parseClarifyingAnswerContent(last.content ?? "") !== null;
  }, [
    messages,
    firstUserMessageId,
    allClarityBlocks.length,
    hasRefinementFinalize,
  ]);
  const isRefinementStageActive = useMemo(() => {
    if (hasRefinementFinalize) return false;
    if (
      isDeepResearchLocked(experimentStatus) ||
      (researchStarted && allClarityBlocks.length > 0)
    ) {
      return false;
    }
    return true;
  }, [
    hasRefinementFinalize,
    experimentStatus,
    researchStarted,
    allClarityBlocks.length,
  ]);
  const showQuestionBlock =
    pendingQuestionBlock !== null &&
    !loading &&
    isRefinementStageActive;
  const isQuestionsLoading =
    loading && !researchStarted && awaitingRefinementAfterUser;
  const awaitingServerReply =
    awaitingRefinementAfterUser &&
    !loading &&
    !showQuestionBlock &&
    isRefinementStageActive;
  const showQuestionsLoadingUi = isQuestionsLoading || awaitingServerReply;
  const showPressureTestSummary = useMemo(() => {
    if (allClarityBlocks.length === 0) return false;
    if (showQuestionBlock || showQuestionsLoadingUi) return false;
    if (hasRefinementFinalize) return true;
    if (researchStarted || isDeepResearchLocked(experimentStatus)) return true;
    return !awaitingRefinementAfterUser;
  }, [
    allClarityBlocks.length,
    showQuestionBlock,
    showQuestionsLoadingUi,
    hasRefinementFinalize,
    researchStarted,
    experimentStatus,
    awaitingRefinementAfterUser,
  ]);
  const inputDisabled = chatDisabled || showQuestionBlock;
  const showChatLoading = loading && !isQuestionsLoading;

  useEffect(() => {
    if (!awaitingServerReply) return;
    const expId = resolvedExperimentId ?? experimentId;
    if (!expId) return;

    let cancelled = false;

    async function poll() {
      if (cancelled) return;
      await refreshChatMessages();
    }

    void poll();
    const intervalId = window.setInterval(() => void poll(), 4000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [awaitingServerReply, resolvedExperimentId, experimentId, refreshChatMessages]);

  function handleQuestionSubmit(answers: ClarifyingQuestionAnswer[]) {
    if (!pendingQuestionBlock) return;
    const text = formatClarifyingAnswers(
      pendingQuestionBlock.questions,
      answers,
    );
    void handleSend(text, true);
  }

  const deepResearchLocked =
    researchStarted || isDeepResearchLocked(experimentStatus);
  const showValidationPrompt = shouldShowValidationResearchPrompt(
    hasRefinementFinalize,
    researchStarted,
    experimentStatus,
    hasValidationReport,
  );
  const showEmptyState =
    messages.length === 0 && !loading && !historyLoading && !experimentId;

  const showChatInput = useMemo(() => {
    const isIdeaIntake =
      messages.length === 0 &&
      !historyLoading &&
      !experimentId &&
      !resolvedExperimentId;
    if (isIdeaIntake) return true;
    return hasValidationReport;
  }, [
    messages.length,
    historyLoading,
    experimentId,
    resolvedExperimentId,
    hasValidationReport,
  ]);

  const openCanvas = useCallback(() => {
    setCanvasOpen(true);
  }, []);

  const handleResearchComplete = useCallback(() => {
    setHasValidationReport(true);
    setReportReadyAt((prev) => prev ?? new Date().toISOString());
    setExperimentStatus("RESEARCH_READY");
    notifyExperimentsChanged();
    onExperimentChange?.();
  }, [onExperimentChange]);

  return (
    <div className="flex h-full min-h-0 w-full flex-1 overflow-hidden">
      <div
        className={`flex h-full min-h-0 flex-col overflow-hidden bg-[var(--fv-bg)] ${
          canvasOpen
            ? "hidden w-full lg:flex lg:min-w-[320px] lg:max-w-[45%] lg:shrink-0 lg:w-[40%]"
            : "w-full flex-1"
        }`}
        style={{ transition: "width 350ms cubic-bezier(0.16, 1, 0.3, 1)" }}
      >
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="min-h-0 flex-1 overflow-y-auto px-4 py-6 lg:px-12 lg:py-8"
        >
          <div className="mx-auto w-full">
            {showEmptyState && (
              <div className="flex flex-col items-center py-16 text-center">
                <FivvleLogo size={40} className="mb-4" />
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
                      className="cursor-pointer rounded-full border border-[var(--fv-border)] bg-[var(--fv-surface-2)] px-4 py-2 text-[13px] text-fv-text-soft transition-all duration-200 hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {historyLoading && messages.length === 0 && (
              <div className="flex justify-center py-16">
                <p className="text-sm text-[var(--fv-text-muted)]">
                  Loading conversation…
                </p>
              </div>
            )}

            {(() => {
              const hasThread =
                messages.length > 0 ||
                showQuestionBlock ||
                showQuestionsLoadingUi;
              let pressureTestRendered = false;

              const threadMessages = messages.map((msg, index) => {
                if (
                  msg.role === "assistant" &&
                  msg.turnKind === "refinement_clarify" &&
                  msg.clarifyingQuestions?.length
                ) {
                  return null;
                }

                const isSparkIdea =
                  msg.role === "user" && msg.id === firstUserMessageId;
                const isClarityAnswer =
                  msg.role === "user" &&
                  !isSparkIdea &&
                  parseClarifyingAnswerContent(msg.content);

                if (isClarityAnswer) {
                  if (pressureTestRendered || !showPressureTestSummary) return null;
                  pressureTestRendered = true;
                  return (
                    <PressureTestSection
                      key="pressure-test-unified"
                      blocks={allClarityBlocks}
                      contentKey={clarityContentKey}
                      messageContentById={clarityMessageContentById}
                      canEditMessage={(messageId) =>
                        !inputDisabled &&
                        !!threadId &&
                        isPersistedMessageId(messageId)
                      }
                      onEdit={handleEditMessage}
                    />
                  );
                }

                if (msg.turnKind === "refinement_finalize") {
                  return (
                    <div key={msg.id}>
                      <RefinementThreadMessage
                        id={msg.id}
                        role={msg.role}
                        content={msg.content}
                        turnKind={msg.turnKind}
                        isSparkIdea={isSparkIdea}
                        originalIdea={originalIdea}
                        canEdit={
                          msg.role === "user" &&
                          !inputDisabled &&
                          !!threadId &&
                          isPersistedMessageId(msg.id)
                        }
                        onEdit={handleEditMessage}
                        showRefining={false}
                      />
                      {showValidationPrompt ? (
                        <ValidationResearchPrompt
                          onStart={() => void handleStartValidation()}
                          loading={loading}
                        />
                      ) : null}
                    </div>
                  );
                }

                return (
                  <RefinementThreadMessage
                    key={msg.id}
                    id={msg.id}
                    role={msg.role}
                    content={msg.content}
                    turnKind={msg.turnKind}
                    isSparkIdea={isSparkIdea}
                    originalIdea={originalIdea}
                    canEdit={
                      msg.role === "user" &&
                      !inputDisabled &&
                      !!threadId &&
                      isPersistedMessageId(msg.id)
                    }
                    onEdit={handleEditMessage}
                    showRefining={
                      msg.role === "assistant" &&
                      !researchStarted &&
                      !deepResearchLocked &&
                      index === messages.length - 1 &&
                      !loading &&
                      !showQuestionBlock
                    }
                  />
                );
              });

              if (!hasThread) return null;

              return (
                <article className="ra-story">
                  {threadMessages}
                  {showPressureTestSummary && !pressureTestRendered && (
                    <PressureTestSection
                      key="pressure-test-unified"
                      blocks={allClarityBlocks}
                      contentKey={clarityContentKey}
                      messageContentById={clarityMessageContentById}
                      canEditMessage={(messageId) =>
                        !inputDisabled &&
                        !!threadId &&
                        isPersistedMessageId(messageId)
                      }
                      onEdit={handleEditMessage}
                    />
                  )}
                  {showQuestionBlock && pendingQuestionBlock && (
                    <ClarifyingQuestionBlock
                      variant="ascent"
                      questions={pendingQuestionBlock.questions}
                      questionNumberStart={allClarityBlocks.length + 1}
                      submitting={loading}
                      pastTurns={pastClarifyingTurns}
                      onEditPast={handleEditPastClarifyingAnswer}
                      onSubmit={(answers) => void handleQuestionSubmit(answers)}
                    />
                  )}
                  {showQuestionsLoadingUi && (
                    <ClarifyingQuestionsLoading
                      questionNumber={allClarityBlocks.length + 1}
                      phase={isQuestionsLoading ? "submitting" : "syncing"}
                      onRetry={() => void refreshChatMessages()}
                    />
                  )}
                </article>
              );
            })()}

            {showChatLoading && (
              <div className="fv-msg-enter border-b border-[var(--fv-border)] py-6">
                <div className="mx-auto w-full max-w-full lg:max-w-[680px]">
                  <div className="flex items-start gap-3">
                    <FivvleLogo size={24} />
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

            {researchStarted && resolvedExperimentId && (
              <InlineResearchProgress
                experimentId={resolvedExperimentId}
                reportReady={hasValidationReport}
                onComplete={handleResearchComplete}
              />
            )}

            {hasValidationReport && resolvedExperimentId && (
              <div className="mx-auto my-6 w-full max-w-full lg:max-w-[680px]">
                <button
                  type="button"
                  onClick={openCanvas}
                  className="group w-full rounded-xl border border-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)] bg-gradient-to-br from-[color-mix(in_srgb,var(--fv-accent)_10%,transparent)] to-transparent p-5 text-left transition-all hover:border-[var(--fv-accent)]/50"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--fv-accent-muted)]">
                      <FileText className="h-6 w-6 text-[var(--fv-accent)]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-[var(--fv-text)]">
                        Validation report ready
                      </p>
                      <p className="mt-0.5 text-sm text-[var(--fv-text-muted)]">
                        {reportReadyAt
                          ? formatReportDate(reportReadyAt)
                          : "View your market research findings"}
                      </p>
                    </div>
                    <span className="fv-btn-primary shrink-0 px-4 py-2 text-sm opacity-90 group-hover:opacity-100">
                      Open report
                    </span>
                  </div>
                </button>
              </div>
            )}

            <div ref={scrollAnchorRef} />
          </div>
        </div>

        {!experimentId && !resolvedExperimentId && showChatInput && (
          <div className="shrink-0 border-t border-[var(--fv-border)] bg-[var(--fv-surface)]/50 px-4 py-3 lg:px-12">
            <label
              htmlFor="project-name"
              className="mb-1.5 block text-[12px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]"
            >
              Project name{" "}
              <span className="normal-case text-[var(--fv-text-dim)]">
                (optional — AI will suggest one if blank)
              </span>
            </label>
            <input
              id="project-name"
              type="text"
              value={projectName}
              maxLength={100}
              disabled={inputDisabled}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Async Standup, CFO Match"
              className="fv-input w-full max-w-md px-3 py-2 text-sm"
            />
          </div>
        )}

        {showChatInput && (
          <ChatInput
            onSend={handleSend}
            disabled={inputDisabled}
            deepResearchLocked={deepResearchLocked}
            prefillText={prefillText}
            prefillNonce={prefillNonce}
            placeholder={
              hasValidationReport
                ? "Continue the conversation…"
                : "Describe your idea..."
            }
          />
        )}
      </div>

      {canvasOpen && resolvedExperimentId && (
        <div className="fixed inset-0 z-[60] flex min-h-0 flex-col overflow-hidden border-l border-[var(--fv-border)] bg-[var(--fv-bg)] fv-msg-enter lg:relative lg:z-auto lg:min-h-0 lg:flex lg:min-w-0 lg:flex-1 lg:overflow-hidden">
          <ReportCanvas
            experimentId={resolvedExperimentId}
            projectName={projectName || "Validation report"}
            onClose={() => setCanvasOpen(false)}
            mobile
          />
        </div>
      )}
      {paywallModal}
    </div>
  );
}
