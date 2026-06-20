/**
 * GridTrace design tokens — sharp monochrome interface.
 *
 * The product chrome is black, white, and neutral gray. Color is reserved for
 * data meaning: risk states, analytical chart series, map overlays, status and
 * selection. These values mirror the CSS custom properties defined in
 * `apps/web/app/globals.css` and are the source of truth for non-CSS consumers
 * (ECharts canvas rendering, deck.gl layers) that cannot read CSS variables.
 *
 * Light and dark themes are structurally identical; only chrome tokens change.
 */

export interface ChromeTokens {
  background: string;
  surface: string;
  surfaceSubtle: string;
  surfaceStrong: string;
  foreground: string;
  foregroundMuted: string;
  foregroundSubtle: string;
  border: string;
  borderStrong: string;
  inverse: string;
  inverseForeground: string;
  gridLine: string;
  focusRing: string;
}

export const LIGHT_CHROME: ChromeTokens = {
  background: "#F4F4F2",
  surface: "#FFFFFF",
  surfaceSubtle: "#ECECEA",
  surfaceStrong: "#E2E2DE",
  foreground: "#0A0A0A",
  foregroundMuted: "#5C5C58",
  foregroundSubtle: "#858580",
  border: "#CFCFC9",
  borderStrong: "#1A1A1A",
  inverse: "#0A0A0A",
  inverseForeground: "#FFFFFF",
  gridLine: "#D8D8D3",
  focusRing: "#0A0A0A",
};

export const DARK_CHROME: ChromeTokens = {
  background: "#080808",
  surface: "#111111",
  surfaceSubtle: "#181818",
  surfaceStrong: "#222222",
  foreground: "#F5F5F2",
  foregroundMuted: "#A5A5A0",
  foregroundSubtle: "#777772",
  border: "#2D2D2A",
  borderStrong: "#F5F5F2",
  inverse: "#F5F5F2",
  inverseForeground: "#080808",
  gridLine: "#262624",
  focusRing: "#F5F5F2",
};

/** Semantic data colors — constant across themes so meaning stays stable. */
export const SEMANTIC_COLORS = {
  riskLow: "#4B8B67",
  riskWatch: "#B08D33",
  riskMedium: "#D8752B",
  riskHigh: "#D13F32",
  riskCritical: "#A51515",
  information: "#2E67C7",
  positive: "#3C8D63",
  negative: "#C73A35",
  warning: "#B88923",
  neutralSeries1: "#6F6F6A",
  neutralSeries2: "#A7A79F",
  comparisonSeries: "#4B6F9E",
  forecastSeries: "#7C5AA6",
  /** Interface selection — kept separate from the risk scale. */
  selectedMapFeature: "#2E67C7",
} as const;

export type SemanticColorKey = keyof typeof SEMANTIC_COLORS;

/** Shape language: sharp, disciplined, minimal radius. */
export const SHAPE = {
  radius: "0.25rem",
  radiusBadge: "2px",
  radiusCard: "4px",
} as const;
