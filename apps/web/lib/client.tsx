"use client";

import {
  assetQueries,
  createGridTraceClient,
  customerQueries,
  dashboardQueries,
  gisQueries,
  healthQuery,
  inspectionMutations,
  inspectionQueries,
  modelQueries,
  riskQueries,
  type GridTraceClient,
} from "@gridtrace/api-client";
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { getPublicEnv } from "./env";

export const TOKEN_KEY = "gridtrace.token";

/** MSW demo login issues this literal; it is not a valid API JWT. */
export const DEMO_MSW_TOKEN = "demo-token";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function hasStoredToken(): boolean {
  return getToken() !== null;
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export interface GridTraceApi {
  client: GridTraceClient;
  dashboard: ReturnType<typeof dashboardQueries>;
  assets: ReturnType<typeof assetQueries>;
  customers: ReturnType<typeof customerQueries>;
  risk: ReturnType<typeof riskQueries>;
  gis: ReturnType<typeof gisQueries>;
  inspections: ReturnType<typeof inspectionQueries>;
  models: ReturnType<typeof modelQueries>;
  health: ReturnType<typeof healthQuery>;
  inspectionMutations: ReturnType<typeof inspectionMutations>;
}

const ApiContext = createContext<GridTraceApi | null>(null);

export function ApiProvider({ children }: { children: ReactNode }) {
  const api = useMemo<GridTraceApi>(() => {
    const { NEXT_PUBLIC_API_BASE_URL } = getPublicEnv();
    const client = createGridTraceClient({
      baseUrl: NEXT_PUBLIC_API_BASE_URL,
      getToken,
    });
    return {
      client,
      dashboard: dashboardQueries(client),
      assets: assetQueries(client),
      customers: customerQueries(client),
      risk: riskQueries(client),
      gis: gisQueries(client),
      inspections: inspectionQueries(client),
      models: modelQueries(client),
      health: healthQuery(client),
      inspectionMutations: inspectionMutations(client),
    };
  }, []);

  return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>;
}

export function useApi(): GridTraceApi {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error("useApi must be used within an ApiProvider");
  return ctx;
}
