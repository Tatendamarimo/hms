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
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
};

export async function primeCsrf(): Promise<void> {
  await request<{ detail: string }>("/auth/csrf/");
}
