import type { RiskTier } from "@gridtrace/contracts";

/**
 * ECharts renders to canvas and cannot read CSS custom properties, so charts
 * use an explicit palette aligned with the app's semantic design tokens.
 * Apps may override by passing a `palette` to option generators.
 */
export interface ChartPalette {
  foreground: string;
  muted: string;
  border: string;
  grid: string;
  primary: string;
  info: string;
  success: string;
  warning: string;
  danger: string;
  riskLow: string;
  riskWatch: string;
  riskMedium: string;
  riskHigh: string;
  riskCritical: string;
}

export const DEFAULT_PALETTE: ChartPalette = {
  foreground: "#e6edf3",
  muted: "#8b98a5",
  border: "#2a3441",
  grid: "#1f2730",
  primary: "#3b82f6",
  info: "#38bdf8",
  success: "#22c55e",
  warning: "#f59e0b",
  danger: "#ef4444",
  riskLow: "#22c55e",
  riskWatch: "#84cc16",
  riskMedium: "#f59e0b",
  riskHigh: "#f97316",
  riskCritical: "#ef4444",
};

export function riskTierColor(tier: RiskTier, palette: ChartPalette = DEFAULT_PALETTE): string {
  switch (tier) {
    case "LOW":
      return palette.riskLow;
    case "WATCH":
      return palette.riskWatch;
    case "MEDIUM":
      return palette.riskMedium;
    case "HIGH":
      return palette.riskHigh;
    case "CRITICAL":
      return palette.riskCritical;
  }
}

export const RISK_TIER_SEQUENCE: RiskTier[] = ["LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL"];
