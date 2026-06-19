import type { EntityType } from "./common";

export type RiskTier = "LOW" | "WATCH" | "MEDIUM" | "HIGH" | "CRITICAL";

/** Component scores are each in [0,1]; the composite risk_score is [0,100]. */
export interface RiskComponents {
  supervised_probability: number;
  anomaly_score: number;
  grid_imbalance_score: number;
  peer_score: number;
  spatial_score: number;
}

export interface RiskExplanation {
  feature: string;
  label: string;
  contribution: number;
  direction: "increases" | "decreases";
  detail?: string;
}

export interface RiskScore {
  id: string;
  entity_type: EntityType;
  entity_id: string;
  scored_at: string;
  risk_score: number;
  risk_tier: RiskTier;
  components: RiskComponents;
  confidence: number;
  estimated_loss_kwh: number;
  estimated_loss_value: number;
  currency: string;
  inspection_priority: number;
  explanations: RiskExplanation[];
  model_version: string;
  feature_version: string;
}
