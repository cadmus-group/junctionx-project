import { RISK_TIERS, type RiskTierLabel } from "@gridtrace/config";

export type { RiskTierLabel };
export { RISK_TIERS };

/**
 * Map an authoritative 0-100 risk score (computed by the backend) to its display tier.
 * WARNING: This is a display-only helper. The authoritative score and tier are always
 * computed and persisted by the backend; never recompute the score in the browser.
 */
export function riskTierForScore(score: number): RiskTierLabel {
  const clamped = Math.max(0, Math.min(100, score));
  for (const tier of RISK_TIERS) {
    if (clamped >= tier.min && clamped <= tier.max) return tier.label;
  }
  return "CRITICAL";
}

/** Semantic Tailwind token suffix for a given tier (e.g. `risk-high`). */
export function riskTokenForTier(tier: RiskTierLabel): string {
  return `risk-${tier.toLowerCase()}`;
}

export const RISK_TIER_ORDER: Record<RiskTierLabel, number> = {
  LOW: 0,
  WATCH: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4,
};
