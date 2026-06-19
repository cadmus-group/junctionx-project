import type { AssetType } from "./common";
import type { Point } from "./geojson";
import type { RiskTier } from "./risk";

export interface GridAsset {
  id: string;
  operator_id: string;
  parent_asset_id: string | null;
  asset_type: AssetType;
  external_id: string;
  name: string;
  voltage_level: string | null;
  capacity_kva: number | null;
  geometry: Point | null;
  region_id: string | null;
  risk_tier: RiskTier | null;
  risk_score: number | null;
}

/** Energy reconciliation for a transformer digital twin. */
export interface TransformerReconciliation {
  transformer_id: string;
  name: string;
  period_start: string;
  period_end: string;
  energy_input_kwh: number;
  metered_output_kwh: number;
  estimated_technical_loss_kwh: number;
  unexplained_loss_kwh: number;
  unexplained_loss_ratio: number;
  customer_count: number;
  risk_tier: RiskTier;
  risk_score: number;
  /** Waterfall steps from input -> metered -> technical -> unexplained. */
  waterfall: { label: string; value: number; kind: "input" | "deduction" | "residual" }[];
  currency: string;
  estimated_loss_value: number;
}

export interface AssetCustomerSummary {
  customer_id: string;
  external_ref: string;
  customer_type: string;
  risk_score: number | null;
  risk_tier: RiskTier | null;
  estimated_loss_kwh: number | null;
}
