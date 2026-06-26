export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function parseResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : null;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
}

export async function ensureCsrfToken(): Promise<string> {
  const existing = getCookie("csrftoken");
  if (existing) return existing;

  const response = await fetch(`${API_BASE_URL}/api/csrf/`, {
    credentials: "include",
    headers: { Accept: "application/json" }
  });
  const data = await parseResponse(response);
  if (!response.ok) {
    throw new ApiError("Could not initialize CSRF protection.", response.status, data);
  }
  return getCookie("csrftoken") ?? ((data as { csrfToken?: string } | null)?.csrfToken ?? "");
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRFToken", await ensureCsrfToken());
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
    cache: method === "GET" ? "no-store" : init.cache
  });
  const data = await parseResponse(response);

  if (!response.ok) {
    let message = response.status === 403 ? "Access denied" : "Request failed";
    if (data && typeof data === "object" && "error" in data) {
      message = String((data as { error: unknown }).error);
    }
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function apiJson<T>(path: string, method: "POST" | "PATCH" | "PUT", body: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: formData
  });
}

export function djangoLoginUrl(nextPath: string): string {
  return `${API_BASE_URL}/accounts/login/?next=${encodeURIComponent(nextPath)}`;
}
