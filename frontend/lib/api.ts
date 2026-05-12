import { getFirebaseAuth } from "./firebase";

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
