import type { APIRequestContext } from "@playwright/test";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ShowcaseIds {
  transformerId: string;
  customerId: string;
  externalRef: string;
}

interface Page<T> {
  items: T[];
}

interface GridAsset {
  id: string;
  external_id: string;
}

interface Customer {
  id: string;
  external_ref: string;
}

interface LoginResponse {
  access_token: string;
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function authenticate(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API_BASE}/api/v1/auth/login`, {
    data: { username: "demo_operator", password: "SuperSecret123!" },
  });
  if (!res.ok()) {
    throw new Error(`Login failed: ${res.status()} ${await res.text()}`);
  }
  const body = (await res.json()) as LoginResponse;
  return body.access_token;
}

export async function resolveShowcase(
  request: APIRequestContext,
  token: string
): Promise<ShowcaseIds> {
  const headers = authHeaders(token);

  const txRes = await request.get(
    `${API_BASE}/api/v1/assets?asset_type=transformer&q=TX-001&page_size=1`,
    { headers }
  );
  if (!txRes.ok()) {
    throw new Error(`Assets lookup failed: ${txRes.status()} ${await txRes.text()}`);
  }
  const txPage = (await txRes.json()) as Page<GridAsset>;
  const transformer = txPage.items[0];
  if (!transformer) {
    throw new Error("Showcase transformer TX-001 not found in seeded API");
  }

  const custRes = await request.get(
    `${API_BASE}/api/v1/customers?q=CUST-00001&page_size=1`,
    { headers }
  );
  if (!custRes.ok()) {
    throw new Error(`Customers lookup failed: ${custRes.status()} ${await custRes.text()}`);
  }
  const custPage = (await custRes.json()) as Page<Customer>;
  const customer = custPage.items[0];
  if (!customer) {
    throw new Error("Showcase customer CUST-00001 not found in seeded API");
  }

  return {
    transformerId: transformer.id,
    customerId: customer.id,
    externalRef: customer.external_ref,
  };
}

export const TOKEN_STORAGE_KEY = "gridtrace.token";
