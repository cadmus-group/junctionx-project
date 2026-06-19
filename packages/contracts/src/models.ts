export interface ModelRegistryEntry {
  id: string;
  model_version: string;
  feature_version: string;
  algorithm: string;
  trained_at: string;
  metrics: {
    pr_auc: number;
    precision_at_k: number;
    k: number;
    [key: string]: number;
  };
  is_active: boolean;
  notes: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  database: "ok" | "unavailable";
  demo_mode: boolean;
  time: string;
}
