import { getFirebaseAuth } from "./firebase";
import type {
  ArchiveExperimentResponse,
  ChatTurnResponse,
  Experiment,
  ExperimentAnalytics,
  ExperimentDetail,
  ExperimentSummary,
  FounderDecision,
  GenerateInsightResponse,
  GenerateLandingPageResponse,
  InsightReport,
  LandingPage,
  LandingPagePatch,
  ResearchStatus,
  ValidationReport,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  authenticated?: boolean;
  signal?: AbortSignal;
};

export async function apiFetch<T>(
  path: string,
  opts: FetchOptions = {},
): Promise<T> {
  const { method = "GET", body, authenticated = true, signal } = opts;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authenticated) {
    const auth = getFirebaseAuth();
    const user = auth.currentUser;
    if (!user) {
      throw new ApiError(401, { error: "Not authenticated" }, null);
    }
    const token = await user.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
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
        const parsed = parseInt(retryAfter, 10);
        retryAfterSeconds = isNaN(parsed) ? null : parsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as T;
}

export type UserSyncResponse = {
  id: string;
  email: string | null;
  name: string | null;
};

export async function syncUser(): Promise<UserSyncResponse> {
  return apiFetch<UserSyncResponse>("/users/sync", {
    method: "POST",
    body: {},
  });
}

export async function createExperiment(
  raw_idea: string,
): Promise<ExperimentDetail> {
  return apiFetch<ExperimentDetail>("/experiments", {
    method: "POST",
    body: { raw_idea },
  });
}

export async function getExperiment(id: string): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}`);
}

export async function getValidationReport(
  id: string,
): Promise<ValidationReport> {
  return apiFetch<ValidationReport>(`/experiments/${id}/validation-report`);
}

export async function listExperiments(): Promise<ExperimentSummary[]> {
  return apiFetch<ExperimentSummary[]>("/experiments");
}

export type ChatTurnParams = {
  message: string;
  deep_research: boolean;
  thread_id?: string | null;
  experiment_id?: string | null;
  idempotency_key?: string;
};

export async function chatTurn(
  params: ChatTurnParams,
): Promise<ChatTurnResponse> {
  const body: Record<string, unknown> = {
    message: params.message,
    deep_research: params.deep_research,
    thread_id: params.thread_id ?? null,
    experiment_id: params.experiment_id ?? null,
  };

  if (params.deep_research) {
    body.idempotency_key =
      params.idempotency_key ?? crypto.randomUUID();
  }

  return apiFetch<ChatTurnResponse>("/chat/turn", {
    method: "POST",
    body,
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
): Promise<LandingPage> {
  return apiFetch<LandingPage>(`/experiments/${experimentId}/landing-page`, {
    method: "PATCH",
    body: patch,
  });
}

export async function generateLandingPage(
  id: string,
  page_goal?: string,
  template_id?: string,
): Promise<GenerateLandingPageResponse> {
  const body: { page_goal?: string; template_id?: string } = {};
  if (page_goal !== undefined) body.page_goal = page_goal;
  if (template_id !== undefined) body.template_id = template_id;
  return apiFetch<GenerateLandingPageResponse>(
    `/experiments/${id}/generate-landing-page`,
    {
      method: "POST",
      body,
    },
  );
}

export async function getExperimentAnalytics(
  id: string,
): Promise<ExperimentAnalytics> {
  return apiFetch<ExperimentAnalytics>(`/experiments/${id}/analytics`);
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
  outcome: FounderDecision,
): Promise<ArchiveExperimentResponse> {
  return apiFetch<ArchiveExperimentResponse>(`/experiments/${id}/archive`, {
    method: "POST",
    body: { outcome },
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
  await apiFetch<void>(`/experiments/${slug}/waitlist`, {
    method: "POST",
    body: { email },
    authenticated: false,
  });
}

export type PublishProjectResponse = {
  message: string;
  slug: string;
  public_url: string;
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
      `${API_BASE}/experiments/${experimentId}/landing-page/logo`,
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
