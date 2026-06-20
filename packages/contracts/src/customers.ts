import type { Point } from "./geojson";
import type { RiskScore, RiskTier } from "./risk";

export interface Customer {
  id: string;
  operator_id: string;
  external_ref: string;
  transformer_id: string | null;
  feeder_id: string | null;
  region_id: string | null;
  customer_type: string;
  tariff_type: string | null;
  building_type: string | null;
  baseline_annual_kwh: number | null;
  street_smartmeter_perc: number | null;
  geometry: Point | null;
  risk_score: number | null;
  risk_tier: RiskTier | null;
}

export interface MeterReading {
  timestamp: string;
  consumption_kwh: number;
  voltage: number | null;
  current: number | null;
  power_factor: number | null;
  reading_quality: string;
  source: string;
}

export interface CustomerReadings {
  customer_id: string;
  unit: "kWh";
  readings: MeterReading[];
}

export interface PeerComparisonPoint {
  timestamp: string;
  customer_kwh: number;
  peer_median_kwh: number;
  expected_kwh: number;
}

export interface CustomerRiskProfile {
  customer: Customer;
  risk: RiskScore;
  peer_comparison: PeerComparisonPoint[];
  spatial_context?: SpatialContext | null;
  /** Attribution share of the parent transformer's unexplained loss [0,1]. */
  loss_attribution_share: number;
  notes: string[];
}

export interface SpatialContext {
  baseline_annual_kwh: number | null;
  street_smartmeter_perc: number | null;
  recent_annualized_kwh: number | null;
  baseline_deviation_ratio: number | null;
}
