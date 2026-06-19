import type { ProblemDetail } from "@gridtrace/contracts";

export interface GridTraceClientOptions {
  baseUrl: string;
  /** Returns a bearer token to inject, or null when unauthenticated. */
  getToken?: () => string | null | undefined;
  /** Generate a request correlation id. Defaults to crypto.randomUUID. */
  correlationId?: () => string;
  fetchImpl?: typeof fetch;
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail;

  constructor(problem: ProblemDetail) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
}

function buildUrl(
  baseUrl: string,
  path: string,
  query?: RequestOptions["query"]
): string {
  const url = new URL(path.replace(/^\//, ""), baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export interface GridTraceClient {
  request<T>(path: string, options?: RequestOptions): Promise<T>;
  baseUrl: string;
}

export function createGridTraceClient(options: GridTraceClientOptions): GridTraceClient {
  const {
    baseUrl,
    getToken,
    fetchImpl = fetch,
    correlationId = () =>
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2),
  } = options;

  async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const { signal, query, body, method = "GET" } = opts;
    const headers: Record<string, string> = {
      Accept: "application/json",
      "X-Correlation-Id": correlationId(),
    };
    const token = getToken?.();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";

    let response: Response;
    try {
      response = await fetchImpl(buildUrl(baseUrl, path, query), {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal,
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      throw new ApiError({
        type: "about:blank",
        title: "Network error",
        status: 0,
        detail: err instanceof Error ? err.message : "Request failed",
      });
    }

    if (response.status === 204) return undefined as T;

    const text = await response.text();
    const data = text ? JSON.parse(text) : undefined;

    if (!response.ok) {
      const problem: ProblemDetail =
        data && typeof data === "object" && "status" in data
          ? (data as ProblemDetail)
          : {
              type: "about:blank",
              title: response.statusText || "Request failed",
              status: response.status,
              detail: typeof data === "string" ? data : undefined,
            };
      throw new ApiError(problem);
    }

    return data as T;
  }

  return { request, baseUrl };
}
