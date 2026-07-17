/**
 * Session-cookie API client. CSRF token is read from the cookie Django sets
 * (GET /auth/csrf/ primes it) and echoed back in the X-CSRFToken header on
 * unsafe methods. Credentials always included — auth is the httpOnly session
 * cookie, never a token in JS.
 */

const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    /** Parsed error body — DRF's {field: [messages]} shape for form errors. */
    public body: unknown = null,
  ) {
    super(detail);
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (method !== "GET" && method !== "HEAD") {
    headers.set("Content-Type", "application/json");
    const csrf = getCookie("csrftoken");
    if (csrf) headers.set("X-CSRFToken", csrf);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = response.statusText;
    let errorBody: unknown = null;
    try {
      errorBody = await response.json();
      const parsed = errorBody as { detail?: string };
      detail = parsed.detail ?? JSON.stringify(errorBody);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail, errorBody);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  /** Router list endpoints are cursor-paginated ({next, previous, results});
   * action/APIView lists are plain arrays. Accept both. */
  list: async <T>(path: string): Promise<T[]> => {
    const data = await request<T[] | { results: T[] }>(path);
    return Array.isArray(data) ? data : data.results;
  },
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
};

export async function primeCsrf(): Promise<void> {
  await request<{ detail: string }>("/auth/csrf/");
}
