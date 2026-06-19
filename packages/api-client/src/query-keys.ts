/** Centralized TanStack Query key factory. */
export const queryKeys = {
  dashboard: {
    summary: (params?: Record<string, unknown>) => ["dashboard", "summary", params] as const,
    lossTrend: (params?: Record<string, unknown>) =>
      ["dashboard", "loss-trend", params] as const,
  },
  gis: {
    anomalies: (params?: Record<string, unknown>) => ["gis", "anomalies", params] as const,
    hotspots: (params?: Record<string, unknown>) => ["gis", "hotspots", params] as const,
  },
  assets: {
    list: (params?: Record<string, unknown>) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
    reconciliation: (id: string) => ["assets", "transformer", id, "reconciliation"] as const,
    customers: (id: string, params?: Record<string, unknown>) =>
      ["assets", id, "customers", params] as const,
  },
  customers: {
    list: (params?: Record<string, unknown>) => ["customers", "list", params] as const,
    detail: (id: string) => ["customers", "detail", id] as const,
    readings: (id: string, params?: Record<string, unknown>) =>
      ["customers", id, "readings", params] as const,
    riskProfile: (id: string) => ["customers", id, "risk-profile"] as const,
  },
  inspections: {
    queue: (params?: Record<string, unknown>) => ["inspections", "queue", params] as const,
    missions: () => ["inspections", "missions"] as const,
    mission: (id: string) => ["inspections", "mission", id] as const,
  },
  models: {
    list: () => ["models", "list"] as const,
  },
  health: () => ["health"] as const,
} as const;
