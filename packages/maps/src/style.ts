import { MAP_DEFAULTS } from "@gridtrace/config";
import type { RiskTier } from "@gridtrace/contracts";

export type RGBAColor = [number, number, number, number];

/** Risk tier colors as RGBA arrays for deck.gl layers. */
export const RISK_TIER_RGBA: Record<RiskTier, RGBAColor> = {
  LOW: [34, 197, 94, 200],
  WATCH: [132, 204, 22, 200],
  MEDIUM: [245, 158, 11, 210],
  HIGH: [249, 115, 22, 220],
  CRITICAL: [239, 68, 68, 235],
};

export const TRANSFORMER_RGBA: RGBAColor = [56, 189, 248, 230];
export const ROUTE_RGBA: RGBAColor = [59, 130, 246, 230];

export function riskTierRgba(tier: RiskTier | null | undefined): RGBAColor {
  return tier ? RISK_TIER_RGBA[tier] : [139, 152, 165, 160];
}

/** Map score [0,100] to an interpolated red intensity for continuous fills. */
export function riskScoreRgba(score: number | null | undefined, alpha = 200): RGBAColor {
  if (score == null) return [139, 152, 165, 120];
  const t = Math.max(0, Math.min(1, score / 100));
  const r = Math.round(34 + t * (239 - 34));
  const g = Math.round(197 - t * (197 - 68));
  const b = Math.round(94 - t * (94 - 68));
  return [r, g, b, alpha];
}

export interface MapStyleConfiguration {
  styleUrl: string;
  center: [number, number];
  zoom: number;
  minZoom: number;
  maxZoom: number;
  customerDetailMinZoom: number;
}

export function mapStyleConfiguration(
  overrides: Partial<MapStyleConfiguration> = {}
): MapStyleConfiguration {
  return {
    styleUrl: "https://demotiles.maplibre.org/style.json",
    center: MAP_DEFAULTS.center,
    zoom: MAP_DEFAULTS.zoom,
    minZoom: MAP_DEFAULTS.minZoom,
    maxZoom: MAP_DEFAULTS.maxZoom,
    customerDetailMinZoom: MAP_DEFAULTS.customerDetailMinZoom,
    ...overrides,
  };
}
