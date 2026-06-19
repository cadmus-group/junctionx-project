import type { RiskTier } from "./risk";

export interface DashboardSummary {
  total_customers: number;
  total_transformers: number;
  total_unexplained_loss_kwh: number;
  total_estimated_loss_value: number;
  currency: string;
  period_start: string;
  period_end: string;
  high_risk_count: number;
  critical_risk_count: number;
  open_inspections: number;
  risk_tier_breakdown: { tier: RiskTier; count: number }[];
  model_version: string;
  feature_version: string;
}

export interface LossTrendPoint {
  timestamp: string;
  energy_input_kwh: number;
  metered_output_kwh: number;
  technical_loss_kwh: number;
  unexplained_loss_kwh: number;
}

export interface LossTrend {
  unit: "kWh";
  points: LossTrendPoint[];
}
