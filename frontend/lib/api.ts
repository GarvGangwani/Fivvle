import { getFirebaseAuth } from "./firebase";
import type {
  ExperimentDetail,
  ExperimentSummary,
  GenerateLandingPageResponse,
  ResearchStatus,
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

export async function getExperiment(id: string): Promise<ExperimentDetail> {
  return apiFetch<ExperimentDetail>(`/experiments/${id}`);
}

export async function listExperiments(): Promise<ExperimentSummary[]> {
  return apiFetch<ExperimentSummary[]>("/experiments");
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

export async function generateInsight(
  id: string,
): Promise<GenerateLandingPageResponse> {
  return apiFetch<GenerateLandingPageResponse>(
    `/experiments/${id}/generate-insight`,
    {
      method: "POST",
      body: {},
    },
  );
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
