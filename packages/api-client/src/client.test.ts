import { describe, expect, it, vi } from "vitest";
import { ApiError, createGridTraceClient } from "./client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFetch(response: Response) {
  return vi.fn((_input: RequestInfo | URL, _init?: RequestInit) =>
    Promise.resolve(response)
  );
}

describe("createGridTraceClient", () => {
  it("builds URLs with the v1 prefix, query params, and correlation id header", async () => {
    const fetchImpl = mockFetch(jsonResponse({ ok: true }));
    const client = createGridTraceClient({
      baseUrl: "http://api.test",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    await client.request("api/v1/customers", { query: { page: 2, q: "abc" } });

    const call = fetchImpl.mock.calls[0]!;
    expect(String(call[0])).toBe("http://api.test/api/v1/customers?page=2&q=abc");
    expect(call[1]?.headers).toHaveProperty("X-Correlation-Id");
  });

  it("injects the bearer token when provided", async () => {
    const fetchImpl = mockFetch(jsonResponse({ ok: true }));
    const client = createGridTraceClient({
      baseUrl: "http://api.test",
      getToken: () => "tok123",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    await client.request("api/v1/health");

    const headers = fetchImpl.mock.calls[0]![1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok123");
  });

  it("throws a typed ApiError carrying the problem detail", async () => {
    const problem = { type: "about:blank", title: "Not found", status: 404 };
    const fetchImpl = mockFetch(jsonResponse(problem, 404));
    const client = createGridTraceClient({
      baseUrl: "http://api.test",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    await expect(client.request("api/v1/customers/x")).rejects.toBeInstanceOf(ApiError);
  });
});
