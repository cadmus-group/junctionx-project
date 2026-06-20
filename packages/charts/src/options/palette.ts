import type { RiskTier } from "@gridtrace/contracts";

/**
 * ECharts renders to canvas and cannot read CSS custom properties, so charts
 * use an explicit palette aligned with the app's semantic design tokens.
 * Apps may override by passing a `palette` to option generators.
 */
export interface ChartPalette {
  /** Chrome — monochrome. */
  foreground: string;
  muted: string;
  border: string;
  grid: string;
  /** Primary analytical line — strong neutral foreground (monochrome). */
  primary: string;
  /** Semantic data colors. */
  info: string;
  success: string;
  warning: string;
  danger: string;
  comparison: string;
  forecast: string;
  neutral1: string;
  neutral2: string;
  riskLow: string;
  riskWatch: string;
  riskMedium: string;
  riskHigh: string;
  riskCritical: string;
}

/**
 * ECharts renders to canvas and cannot read CSS custom properties. This palette
 * mirrors the dark-theme monochrome chrome plus the constant semantic data
 * colors from `@gridtrace/config`. Chart chrome stays monochrome; series colors
 * carry meaning. Apps may pass a `palette` to override per theme.
 */
export const DEFAULT_PALETTE: ChartPalette = {
  foreground: "#F5F5F2",
  muted: "#A5A5A0",
  border: "#2D2D2A",
  grid: "#262624",
  primary: "#F5F5F2",
  info: "#2E67C7",
  success: "#3C8D63",
  warning: "#B88923",
  danger: "#C73A35",
  comparison: "#4B6F9E",
  forecast: "#7C5AA6",
  neutral1: "#6F6F6A",
  neutral2: "#A7A79F",
  riskLow: "#4B8B67",
  riskWatch: "#B08D33",
  riskMedium: "#D8752B",
  riskHigh: "#D13F32",
  riskCritical: "#A51515",
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
