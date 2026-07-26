import type { User as FirebaseUser } from "firebase/auth";
import { getFirebaseAuth } from "./firebase";
import { handleSessionExpired } from "./session-expired";
import { createSSEParser, type SSEEvent } from "./sse-parser";
import type {
  ArchiveExperimentResponse,
  ChatHistoryMessage,
  ChatTurnResponse,
  DeleteExperimentResponse,
  Experiment,
  ExperimentAnalytics,
  ExperimentChatMessagesResponse,
  ChatEditTurnResponse,
  EvidenceChatActivateResponse,
  EvidenceChatEditRequest,
  EvidenceChatEditResponse,
  EvidenceChatFeedbackResponse,
  EvidenceChatMessagesResponse,
  EvidenceChatRegenerateRequest,
  EvidenceChatRegenerateResponse,
  EvidenceChatSendRequest,
  EvidenceChatSendResponse,
  EvidenceChatStreamDone,
  EvidenceChatVerdict,
  ExperimentDetail,
  ExperimentSummary,
  SearchResult,
  FounderDecision,
  GenerateInsightResponse,
  GenerateLandingPageResponse,
  InsightReport,
  LandingPage,
  LandingPagePatch,
  LandingPageSlugAvailability,
  ResearchStatus,
  UniversalChatMessagesResponse,
  UniversalChatSendResponse,
  ValidationReport,
  WaitlistSignupsResponse,
} from "./types";
const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export class ApiError extends Error {
  public retryAfterSeconds: number | null;

  constructor(
    public status: number,
    public body: unknown,
    public requestId: string | null,
    retryAfterSeconds: number | null = null,
  ) {
    super(`API ${status}`);
    this.name = "ApiError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

type FetchOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  authenticated?: boolean;
  /** When set, skips auth.currentUser and uses this token directly. */
  idToken?: string;
  signal?: AbortSignal;
};

/**
 * Resolve the Firebase auth header. Single source of truth for token
 * acquisition — used by apiFetch and by hand-rolled fetches (e.g. SSE streaming)
 * that can't route through apiFetch. Triggers the session-expired flow and
 * throws a 401 ApiError when there is no signed-in user.
 */
export async function getAuthHeader(
  idToken?: string,
): Promise<Record<string, string>> {
  let token = idToken;
  if (!token) {
    const auth = getFirebaseAuth();
    const user = auth.currentUser;
    if (!user) {
      await handleSessionExpired();
      throw new ApiError(401, { error: "Not authenticated" }, null);
    }
    token = await user.getIdToken();
  }
  return { Authorization: `Bearer ${token}` };
}

export async function apiFetch<T>(
  path: string,
  opts: FetchOptions = {},
): Promise<T> {
  const { method = "GET", body, authenticated = true, idToken, signal } = opts;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authenticated) {
    Object.assign(headers, await getAuthHeader(idToken));
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const raw = await response.text();
    parsed = raw ? JSON.parse(raw) : null;
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const parsedRetryAfter = parseInt(retryAfter, 10);
        retryAfterSeconds = Number.isNaN(parsedRetryAfter)
          ? null
          : parsedRetryAfter;
      }
    }
    if (response.status === 401 && authenticated) {
      await handleSessionExpired();
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as T;
}

export type UserSyncResponse = {
  id: string;
  email: string | null;
  name: string | null;
  is_admin: boolean;
  created_at?: string;
};

export async function syncUser(
  firebaseUser?: FirebaseUser,
): Promise<UserSyncResponse> {
  const user = firebaseUser ?? getFirebaseAuth().currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const idToken = await user.getIdToken();
  return apiFetch<UserSyncResponse>("/users/sync", {
    method: "POST",
    body: {},
    idToken,
  });
}

export async function createExperiment(
  name: string,
): Promise<{ id: string }> {
  return apiFetch<{ id: string }>("/experiments", {
    method: "POST",
    body: { name: name.trim() },
  });
}

export async function getExperiment(id: string): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}`);
}

export async function renameExperiment(
  id: string,
  name: string,
): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}/name`, {
    method: "PATCH",
    body: { name },
  });
}

export async function getValidationReport(
  id: string,
): Promise<ValidationReport> {
  return apiFetch<ValidationReport>(`/experiments/${id}/validation-report`);
}

export interface EditedDocResponse {
  doc: object;
  version: number;
  source: "generated" | "persisted";
  is_stale_since_regeneration: boolean;
}

/** Raised when a PATCH to the edited-doc endpoint loses the CAS race (409). */
export class EditedDocVersionConflict extends ApiError {
  public current_version: number;

  constructor(current_version: number, body: unknown, requestId: string | null) {
    super(409, body, requestId);
    this.name = "EditedDocVersionConflict";
    this.current_version = current_version;
  }
}

export async function getEditedDoc(
  experimentId: string,
): Promise<EditedDocResponse> {
  return apiFetch<EditedDocResponse>(
    `/experiments/${experimentId}/validation-report/edited-doc`,
  );
}

export async function patchEditedDoc(
  experimentId: string,
  body: { doc: object; base_version: number },
): Promise<EditedDocResponse> {
  try {
    return await apiFetch<EditedDocResponse>(
      `/experiments/${experimentId}/validation-report/edited-doc`,
      { method: "PATCH", body },
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) {
      const detail = (err.body as { detail?: { current_version?: number } })
        ?.detail;
      const current =
        typeof detail?.current_version === "number"
          ? detail.current_version
          : 0;
      throw new EditedDocVersionConflict(current, err.body, err.requestId);
    }
    throw err;
  }
}

export async function listExperiments(options?: {
  archived?: boolean;
}): Promise<ExperimentSummary[]> {
  const params = new URLSearchParams();
  if (options?.archived) {
    params.set("archived", "true");
  }
  const query = params.toString();
  return apiFetch<ExperimentSummary[]>(
    query ? `/experiments?${query}` : "/experiments",
  );
}

export async function searchExperiments(q: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q });
  return apiFetch<SearchResult[]>(`/search?${params.toString()}`);
}

export type ChatTurnParams = {
  message: string;
  deep_research: boolean;
  thread_id?: string | null;
  experiment_id?: string | null;
  idempotency_key?: string;
  name?: string | null;
  attachment_ids?: string[];
  selected_option_indices?: number[] | null;
  custom_added_text?: string | null;
  answered_question_from_message_id?: string | null;
  signal?: AbortSignal;
};

export type ChatAttachmentUploadItem = {
  id: string;
  filename: string;
  content_kind: string;
  excerpt: string;
  char_count: number;
};

export async function uploadChatAttachments(
  files: File[],
): Promise<ChatAttachmentUploadItem[]> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const token = await user.getIdToken();

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  let response: Response;
  try {
    response = await fetch(apiUrl("/chat/attachments"), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");
  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    parsed = await response.json();
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const retryParsed = parseInt(retryAfter, 10);
        retryAfterSeconds = Number.isNaN(retryParsed) ? null : retryParsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  const data = parsed as { attachments: ChatAttachmentUploadItem[] };
  return data.attachments;
}

export async function chatTurn(
  params: ChatTurnParams,
): Promise<ChatTurnResponse> {
  const body: Record<string, unknown> = {
    message: params.message,
    deep_research: params.deep_research,
    thread_id: params.thread_id ?? null,
    experiment_id: params.experiment_id ?? null,
    attachment_ids: params.attachment_ids ?? [],
  };

  if (params.name?.trim()) {
    body.name = params.name.trim();
  }

  if (params.deep_research) {
    body.idempotency_key =
      params.idempotency_key ?? crypto.randomUUID();
  }

  if (params.selected_option_indices != null) {
    body.selected_option_indices = params.selected_option_indices;
  }
  if (params.custom_added_text != null) {
    body.custom_added_text = params.custom_added_text;
  }
  if (params.answered_question_from_message_id != null) {
    body.answered_question_from_message_id =
      params.answered_question_from_message_id;
  }

  return apiFetch<ChatTurnResponse>("/chat/turn", {
    method: "POST",
    body,
    signal: params.signal,
  });
}

export async function getExperimentChatMessages(
  experimentId: string,
): Promise<ExperimentChatMessagesResponse> {
  return apiFetch<ExperimentChatMessagesResponse>(
    `/chat/experiments/${experimentId}/messages`,
  );
}

export async function getEvidenceChatMessages(
  experimentId: string,
): Promise<EvidenceChatMessagesResponse> {
  return apiFetch<EvidenceChatMessagesResponse>(
    `/experiments/${experimentId}/evidence-chat/messages`,
  );
}

export async function getUniversalChatMessages(
  experimentId: string,
): Promise<UniversalChatMessagesResponse> {
  return apiFetch<UniversalChatMessagesResponse>(
    `/experiments/${experimentId}/chat/universal/messages`,
  );
}

export async function sendUniversalChatMessage(
  experimentId: string,
  message: string,
): Promise<UniversalChatSendResponse> {
  return apiFetch<UniversalChatSendResponse>(
    `/experiments/${experimentId}/chat/universal`,
    { method: "POST", body: { message } },
  );
}

export async function sendEvidenceChatMessage(
  experimentId: string,
  body: EvidenceChatSendRequest,
): Promise<EvidenceChatSendResponse> {
  return apiFetch<EvidenceChatSendResponse>(
    `/experiments/${experimentId}/evidence-chat`,
    { method: "POST", body },
  );
}

export async function regenerateEvidenceChatMessage(
  experimentId: string,
  assistantMessageId: string,
  body: EvidenceChatRegenerateRequest,
): Promise<EvidenceChatRegenerateResponse> {
  return apiFetch<EvidenceChatRegenerateResponse>(
    `/experiments/${experimentId}/evidence-chat/messages/${assistantMessageId}/regenerate`,
    { method: "POST", body },
  );
}

export async function sendEvidenceChatFeedback(
  experimentId: string,
  messageId: string,
  verdict: EvidenceChatVerdict,
): Promise<EvidenceChatFeedbackResponse> {
  return apiFetch<EvidenceChatFeedbackResponse>(
    `/experiments/${experimentId}/evidence-chat/messages/${messageId}/feedback`,
    { method: "POST", body: { verdict } },
  );
}

export async function editEvidenceChatMessage(
  experimentId: string,
  userMessageId: string,
  body: EvidenceChatEditRequest,
): Promise<EvidenceChatEditResponse> {
  return apiFetch<EvidenceChatEditResponse>(
    `/experiments/${experimentId}/evidence-chat/messages/${userMessageId}/edit`,
    { method: "POST", body },
  );
}

export async function activateEvidenceChatBranch(
  experimentId: string,
  messageId: string,
): Promise<EvidenceChatActivateResponse> {
  return apiFetch<EvidenceChatActivateResponse>(
    `/experiments/${experimentId}/evidence-chat/messages/${messageId}/activate`,
    { method: "POST" },
  );
}

export interface StreamEvidenceCallbacks {
  onToken: (text: string) => void;
  onDone: (payload: EvidenceChatStreamDone) => void;
  onError: (message: string) => void;
}

/**
 * Stream an evidence-chat reply over SSE (fetch + ReadableStream, manual frame
 * parsing). Tokens arrive via `onToken`; completion via `onDone`; a server-side
 * `error` frame or a mid-stream network drop via `onError`. A non-OK initial
 * response throws an ApiError (surface it before any tokens). An aborted
 * `signal` (component unmount) resolves silently with no callback.
 */
export async function streamEvidenceChatMessage(
  experimentId: string,
  body: EvidenceChatSendRequest,
  callbacks: StreamEvidenceCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const authHeader = await getAuthHeader();

  let response: Response;
  try {
    response = await fetch(
      apiUrl(`/experiments/${experimentId}/evidence-chat/stream`),
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify(body),
        signal,
      },
    );
  } catch (err) {
    if (signal?.aborted) return;
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");
  if (!response.ok || !response.body) {
    let parsed: unknown = null;
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const raw = await response.text();
      parsed = raw ? JSON.parse(raw) : null;
    } else {
      parsed = await response.text();
    }
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const n = parseInt(retryAfter, 10);
        retryAfterSeconds = Number.isNaN(n) ? null : n;
      }
    }
    if (response.status === 401) {
      await handleSessionExpired();
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  const dispatch = (event: SSEEvent): void => {
    if (event.event === "token") {
      try {
        const data = JSON.parse(event.data) as { text?: string };
        if (typeof data.text === "string") callbacks.onToken(data.text);
      } catch {
        /* ignore malformed token frame */
      }
    } else if (event.event === "done") {
      try {
        callbacks.onDone(JSON.parse(event.data) as EvidenceChatStreamDone);
      } catch {
        callbacks.onError("The reply finished but couldn't be read — retry");
      }
    } else if (event.event === "error") {
      let message = "Evidence chat failed, please try again";
      try {
        const data = JSON.parse(event.data) as { message?: string };
        if (typeof data.message === "string" && data.message.trim()) {
          message = data.message;
        }
      } catch {
        /* keep the default message */
      }
      callbacks.onError(message);
    }
  };

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSSEParser();
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const event of parser.push(decoder.decode(value, { stream: true }))) {
        dispatch(event);
      }
    }
    for (const event of parser.flush()) dispatch(event);
  } catch {
    if (signal?.aborted) return;
    callbacks.onError("Connection lost — retry");
  }
}

export async function finalizeRefinement(
  experimentId: string,
): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${experimentId}/refine/finalize`, {
    method: "POST",
    body: {},
  });
}

export async function resetRefineSession(
  experimentId: string,
): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${experimentId}/refine/session`, {
    method: "DELETE",
  });
}

/** Proactive Refiner opener for an empty Refine thread. 400 if messages exist. */
export async function generateRefinerOpener(
  experimentId: string,
): Promise<ChatHistoryMessage> {
  return apiFetch<ChatHistoryMessage>(
    `/experiments/${experimentId}/refine/opener`,
    {
      method: "POST",
      body: {},
    },
  );
}

export async function retryRefineAssistantMessage(
  experimentId: string,
  messageId: string,
): Promise<ChatTurnResponse> {
  return apiFetch<ChatTurnResponse>(
    `/experiments/${experimentId}/refine/messages/${messageId}/retry`,
    {
      method: "POST",
      body: {},
    },
  );
}

export async function getMessageSiblings(
  experimentId: string,
  messageId: string,
): Promise<ChatHistoryMessage[]> {
  return apiFetch<ChatHistoryMessage[]>(
    `/experiments/${experimentId}/refine/messages/${messageId}/siblings`,
  );
}

export async function setActiveBranch(
  experimentId: string,
  messageId: string,
): Promise<Experiment> {
  return apiFetch<Experiment>(
    `/experiments/${experimentId}/refine/messages/${messageId}/set-active`,
    {
      method: "POST",
      body: {},
    },
  );
}

export async function editChatMessage(
  threadId: string,
  messageId: string,
  newContent: string,
): Promise<ChatEditTurnResponse> {
  return apiFetch<ChatEditTurnResponse>("/chat/turn/edit", {
    method: "POST",
    body: {
      thread_id: threadId,
      message_id: messageId,
      new_content: newContent,
    },
  });
}

export async function refineExperiment(
  id: string,
  feedback?: string,
): Promise<ExperimentDetail> {
  return apiFetch<ExperimentDetail>(`/experiments/${id}/refine`, {
    method: "POST",
    body: feedback !== undefined ? { feedback } : {},
  });
}

export async function confirmExperiment(id: string): Promise<{
  experiment_id: string;
  status: string;
  status_url: string;
  credits_balance: number;
}> {
  return apiFetch(`/experiments/${id}/confirm`, {
    method: "POST",
    body: {},
  });
}

export async function getResearchStatus(id: string): Promise<ResearchStatus> {
  return apiFetch<ResearchStatus>(`/experiments/${id}/research-status`);
}

export async function getLandingPage(
  experimentId: string,
): Promise<LandingPage> {
  return apiFetch<LandingPage>(`/experiments/${experimentId}/landing-page`);
}

export async function patchLandingPage(
  experimentId: string,
  patch: LandingPagePatch,
  options: { signal?: AbortSignal } = {},
): Promise<LandingPage> {
  return apiFetch<LandingPage>(`/experiments/${experimentId}/landing-page`, {
    method: "PATCH",
    body: patch,
    signal: options.signal,
  });
}

export async function checkLandingPageSlugAvailability(
  experimentId: string,
  slug: string,
): Promise<LandingPageSlugAvailability> {
  const params = new URLSearchParams({ slug });
  return apiFetch<LandingPageSlugAvailability>(
    `/experiments/${experimentId}/landing-page/slug-availability?${params.toString()}`,
  );
}

export async function generateLandingPage(
  id: string,
  options: { template_id: string; page_goal?: string; regeneration_hint?: string } = {
    template_id: "dark-premium",
  },
): Promise<GenerateLandingPageResponse> {
  return apiFetch<GenerateLandingPageResponse>(
    `/experiments/${id}/generate-landing-page`,
    {
      method: "POST",
      body: options,
    },
  );
}

export type MetricsAccessResponse = {
  unlocked: boolean;
};

export type UnlockMetricsResponse = {
  unlocked: boolean;
  already_unlocked: boolean;
  credits_balance: number;
};

export async function getMetricsAccess(
  experimentId: string,
): Promise<MetricsAccessResponse> {
  return apiFetch<MetricsAccessResponse>(
    `/experiments/${experimentId}/metrics-access`,
  );
}

export async function unlockMetrics(
  experimentId: string,
): Promise<UnlockMetricsResponse> {
  return apiFetch<UnlockMetricsResponse>(
    `/experiments/${experimentId}/unlock-metrics`,
    { method: "POST", body: {} },
  );
}

export async function getExperimentAnalytics(
  id: string,
): Promise<ExperimentAnalytics> {
  return apiFetch<ExperimentAnalytics>(`/experiments/${id}/analytics`);
}

export async function getWaitlistSignups(
  experimentId: string,
): Promise<WaitlistSignupsResponse> {
  return apiFetch<WaitlistSignupsResponse>(
    `/experiments/${experimentId}/waitlist`,
  );
}

export async function exportWaitlistCsv(experimentId: string): Promise<void> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }

  const token = await user.getIdToken();
  let response: Response;
  try {
    response = await fetch(apiUrl(`/experiments/${experimentId}/waitlist/export`), {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    const parsed = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    throw new ApiError(response.status, parsed, requestId);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = "waitlist.csv";
  const match = disposition?.match(/filename="([^"]+)"/);
  if (match?.[1]) {
    filename = match[1];
  }

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export async function getInsightReport(
  id: string,
): Promise<InsightReport> {
  return apiFetch<InsightReport>(`/experiments/${id}/insight-report`);
}

export async function generateInsight(
  id: string,
): Promise<GenerateInsightResponse> {
  return apiFetch<GenerateInsightResponse>(
    `/experiments/${id}/generate-insight`,
    {
      method: "POST",
      body: {},
    },
  );
}

export async function archiveExperiment(
  id: string,
  outcome: FounderDecision | "manual",
): Promise<ArchiveExperimentResponse> {
  return apiFetch<ArchiveExperimentResponse>(`/experiments/${id}/archive`, {
    method: "POST",
    body: { outcome },
  });
}

export async function archiveProject(
  id: string,
): Promise<ArchiveExperimentResponse> {
  return archiveExperiment(id, "manual");
}

export type FounderDecisionResponse = {
  founder_decision: FounderDecision;
  founder_decision_at: string;
  founder_decision_note: string | null;
  founder_decision_version: number;
};

export type RecordFounderDecisionBody = {
  decision: FounderDecision;
  note?: string | null;
  base_version: number;
};

/** PUT /experiments/{id}/founder-decision — record or amend (CAS on base_version). */
export async function recordFounderDecision(
  id: string,
  body: RecordFounderDecisionBody,
): Promise<FounderDecisionResponse> {
  return apiFetch<FounderDecisionResponse>(
    `/experiments/${id}/founder-decision`,
    { method: "PUT", body },
  );
}

export async function unarchiveExperiment(id: string): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}/unarchive`, {
    method: "POST",
    body: {},
  });
}

export async function deleteProject(id: string): Promise<DeleteExperimentResponse> {
  return apiFetch<DeleteExperimentResponse>(`/experiments/${id}`, {
    method: "DELETE",
    body: { confirmation: "CONFIRM" },
  });
}

export async function submitPageView(
  slug: string,
  source_tag?: string,
): Promise<void> {
  const body: { slug: string; source_tag?: string } = { slug };
  if (source_tag !== undefined) body.source_tag = source_tag;
  await apiFetch<void>("/analytics/page-view", {
    method: "POST",
    body,
    authenticated: false,
  });
}

export async function submitWaitlistSignup(
  slug: string,
  email: string,
): Promise<void> {
  await apiFetch<void>(`/e/${slug}/waitlist`, {
    method: "POST",
    body: { email },
    authenticated: false,
  });
}

export type PublishProjectResponse = {
  message: string;
  slug: string;
  public_url: string;
  publish_number: number;
};

export type PublicationSummary = {
  id: string;
  slug: string;
  public_url: string;
  is_current: boolean;
  output_version: number;
  cta_mode: string;
  published_at: string;
};

export async function publishProject(
  experimentId: string,
  payload: { slug?: string; cta_mode: string; cta_url?: string },
): Promise<PublishProjectResponse> {
  return apiFetch<PublishProjectResponse>(
    `/experiments/${experimentId}/landing-page/publish`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function republishLandingPage(
  experimentId: string,
): Promise<PublishProjectResponse> {
  return apiFetch<PublishProjectResponse>(
    `/experiments/${experimentId}/landing-page/republish`,
    {
      method: "POST",
    },
  );
}

export async function listPublications(
  experimentId: string,
): Promise<PublicationSummary[]> {
  return apiFetch<PublicationSummary[]>(
    `/experiments/${experimentId}/landing-page/publications`,
  );
}

export async function uploadProjectLogo(
  experimentId: string,
  file: File,
): Promise<{ logo_url: string; filename: string }> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const token = await user.getIdToken();

  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(
      apiUrl(`/experiments/${experimentId}/landing-page/logo`),
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    );
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    parsed = await response.json();
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const retryParsed = parseInt(retryAfter, 10);
        retryAfterSeconds = isNaN(retryParsed) ? null : retryParsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as { logo_url: string; filename: string };
}

export async function uploadSectionImage(
  experimentId: string,
  file: File,
): Promise<{ image_url: string; filename: string }> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const token = await user.getIdToken();

  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(
      apiUrl(`/experiments/${experimentId}/landing-page/section-image`),
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    );
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    parsed = await response.json();
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const retryParsed = parseInt(retryAfter, 10);
        retryAfterSeconds = isNaN(retryParsed) ? null : retryParsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as { image_url: string; filename: string };
}

export type ProductCostRow = {
  cost_category: string;
  label: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
};

export type PerProductCostResponse = {
  days_back: number;
  rows: ProductCostRow[];
};

export type DailyCostRow = {
  day: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  tavily_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
};

export type ExperimentCostStatsRow = {
  experiment_count: number;
  avg_cost_usd: string;
  min_cost_usd: string;
  max_cost_usd: string;
  median_cost_usd: string;
};

export type CostSummaryResponse = {
  days_back: number;
  total_cost_usd: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  tavily_logged_cost_usd: string;
  tavily_estimated_gap_usd: string;
  tavily_total_cost_usd: string;
  tavily_logged_credits: number;
  tavily_estimated_gap_credits: number;
  tavily_unlogged_experiment_count: number;
  llm_call_count: number;
  external_api_call_count: number;
  active_user_count: number;
  experiment_stats: ExperimentCostStatsRow;
  target_cost_per_experiment_usd: string;
  tavily_usd_per_credit: string;
};

export type UserCostInsightRow = {
  user_id: string;
  email: string;
  name: string | null;
  experiment_count: number;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
};

export type ExperimentPhaseCostRow = {
  phase: string;
  label: string;
  source: string;
  cost_usd: string;
  call_count: number;
};

export type UserExperimentCostRow = {
  experiment_id: string;
  label: string;
  name: string | null;
  status: string;
  total_cost_usd: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  phases: ExperimentPhaseCostRow[];
};

export type UserExperimentsCostResponse = {
  user_id: string;
  email: string;
  name: string | null;
  days_back: number;
  experiments: UserExperimentCostRow[];
};

export type ProviderCostRow = {
  provider: string;
  source: string;
  cost_usd: string;
  call_count: number;
};

export type PhaseCostRow = {
  phase: string | null;
  llm_cost_usd: string;
  call_count: number;
};

export type TopExperimentCostRow = {
  experiment_id: string;
  label: string;
  total_cost_usd: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
};

export type CostInsightsResponse = {
  days_back: number;
  summary: CostSummaryResponse;
  per_user: UserCostInsightRow[];
  per_provider: ProviderCostRow[];
  per_phase: PhaseCostRow[];
  top_experiments: TopExperimentCostRow[];
};

export type DailyCostResponse = {
  days_back: number;
  rows: DailyCostRow[];
};

export type ExperimentCostResponse = {
  experiment_id: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
  products: ProductCostRow[];
};

export async function getAdminPerProductCost(
  days = 30,
): Promise<PerProductCostResponse> {
  return apiFetch<PerProductCostResponse>(
    `/admin/cost/per-product?days=${days}`,
  );
}

export async function getAdminDailyCost(
  days = 30,
): Promise<DailyCostResponse> {
  return apiFetch<DailyCostResponse>(`/admin/cost/daily?days=${days}`);
}

export async function getAdminExperimentCost(
  experimentId: string,
): Promise<ExperimentCostResponse> {
  return apiFetch<ExperimentCostResponse>(
    `/admin/cost/experiment/${experimentId}`,
  );
}

export async function getAdminCostInsights(
  days = 30,
): Promise<CostInsightsResponse> {
  return apiFetch<CostInsightsResponse>(`/admin/cost/insights?days=${days}`);
}

export async function getAdminUserExperimentsCost(
  userId: string,
  days = 30,
): Promise<UserExperimentsCostResponse> {
  return apiFetch<UserExperimentsCostResponse>(
    `/admin/cost/user/${userId}/experiments?days=${days}`,
  );
}

export type AdminCouponSummary = {
  id: string;
  code: string;
  credits: number;
  enabled: boolean;
  archived_at: string | null;
  max_redemptions: number | null;
  redemption_count: number;
  remaining_redemptions: number | null;
  total_credits_gifted: number;
  total_usd_gifted: string;
  starts_at: string | null;
  ends_at: string | null;
  limit_reached_message: string | null;
  not_yet_active_message: string | null;
  expired_message: string | null;
  disabled_message: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminCouponListResponse = {
  coupons: AdminCouponSummary[];
  total_usd_gifted_all_coupons: string;
};

export type AdminCreateCouponRequest = {
  code: string;
  credits: number;
  enabled?: boolean;
  max_redemptions?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  limit_reached_message?: string | null;
  not_yet_active_message?: string | null;
  expired_message?: string | null;
  disabled_message?: string | null;
};

export type AdminUpdateCouponRequest = {
  credits?: number;
  enabled?: boolean;
  max_redemptions?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  clear_starts_at?: boolean;
  clear_ends_at?: boolean;
  limit_reached_message?: string | null;
  not_yet_active_message?: string | null;
  expired_message?: string | null;
  disabled_message?: string | null;
  clear_limit_reached_message?: boolean;
  clear_not_yet_active_message?: boolean;
  clear_expired_message?: boolean;
  clear_disabled_message?: boolean;
};

export async function getAdminCoupons(
  includeArchived = false,
): Promise<AdminCouponListResponse> {
  const query = includeArchived ? "?include_archived=true" : "";
  return apiFetch<AdminCouponListResponse>(`/admin/coupons${query}`);
}

export async function createAdminCoupon(
  body: AdminCreateCouponRequest,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>("/admin/coupons", {
    method: "POST",
    body,
  });
}

export async function updateAdminCoupon(
  couponId: string,
  body: AdminUpdateCouponRequest,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>(`/admin/coupons/${couponId}`, {
    method: "PATCH",
    body,
  });
}

export async function archiveAdminCoupon(
  couponId: string,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>(`/admin/coupons/${couponId}/archive`, {
    method: "POST",
  });
}

export async function restoreAdminCoupon(
  couponId: string,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>(`/admin/coupons/${couponId}/restore`, {
    method: "POST",
  });
}

export async function deleteAdminCoupon(couponId: string): Promise<void> {
  await apiFetch<void>(`/admin/coupons/${couponId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Wallet (Phase 12)
// ---------------------------------------------------------------------------

export type CreditPack = {
  id: string;
  name: string;
  usd_cents: number;
  usd_display: string;
  base_credits: number;
  bonus_credits: number;
  total_credits: number;
};

export type WalletBalance = {
  credits_balance: number;
  usd_equivalent: string;
  total_credits_purchased: number;
  total_credits_consumed: number;
  credit_conversion_rate: number;
  has_redeemed_welcome_coupon: boolean;
  packs: CreditPack[];
};

export type CreateWalletOrderResponse = {
  payment_order_id: string;
  pack_id: string;
  pack_name: string;
  usd_cents: number;
  base_credits: number;
  bonus_credits: number;
  total_credits: number;
  amount_inr_paise: number;
  currency: string;
  razorpay_key_id: string;
  razorpay_order_id: string;
  receipt: string;
};

export type VerifyWalletPaymentResponse = {
  payment_order_id: string;
  credits_added: number;
  bonus_credits: number;
  new_balance: number;
  already_processed: boolean;
  razorpay_payment_id: string;
  razorpay_order_id: string;
};

export type RedeemCouponResponse = {
  code: string;
  credits_added: number;
  new_balance: number;
};

export type WalletTransactionType =
  | "TOPUP"
  | "BONUS"
  | "COUPON"
  | "SERVICE_USAGE"
  | "REFUND"
  | "ADMIN_ADJUSTMENT";

export type WalletTransaction = {
  id: string;
  type: WalletTransactionType;
  credits: number;
  title: string;
  detail: string | null;
  reference: string | null;
  created_at: string;
  balance_after: number;
  experiment_id: string | null;
  experiment_name: string | null;
};

export type WalletTransactionsResponse = {
  transactions: WalletTransaction[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  credits_balance: number;
  total_credits_purchased: number;
  total_credits_consumed: number;
};

export async function getWallet(): Promise<WalletBalance> {
  return apiFetch<WalletBalance>("/wallet");
}

export async function getWalletTransactions(
  options: { limit?: number; offset?: number } = {},
): Promise<WalletTransactionsResponse> {
  const params = new URLSearchParams();
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options.offset !== undefined) {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  return apiFetch<WalletTransactionsResponse>(
    `/wallet/transactions${query ? `?${query}` : ""}`,
  );
}

export async function createWalletOrder(
  packId: string,
): Promise<CreateWalletOrderResponse> {
  return apiFetch<CreateWalletOrderResponse>("/wallet/orders", {
    method: "POST",
    body: { packId },
  });
}

export async function verifyWalletPayment(body: {
  razorpayPaymentId: string;
  razorpayOrderId: string;
  razorpaySignature: string;
}): Promise<VerifyWalletPaymentResponse> {
  return apiFetch<VerifyWalletPaymentResponse>("/wallet/payments/verify", {
    method: "POST",
    body,
  });
}

export async function redeemWalletCoupon(
  code: string,
): Promise<RedeemCouponResponse> {
  return apiFetch<RedeemCouponResponse>("/wallet/coupons/redeem", {
    method: "POST",
    body: { code },
  });
}
