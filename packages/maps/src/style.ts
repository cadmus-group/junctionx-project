import { MAP_DEFAULTS } from "@gridtrace/config";
import type { RiskTier } from "@gridtrace/contracts";
import type { StyleSpecification } from "maplibre-gl";

export type RGBAColor = [number, number, number, number];

/**
 * Risk tier colors as RGBA arrays for deck.gl layers. These mirror the semantic
 * risk scale in `@gridtrace/config` and are the analytical severity colors —
 * kept deliberately separate from the interface selection color.
 */
export const RISK_TIER_RGBA: Record<RiskTier, RGBAColor> = {
  LOW: [75, 139, 103, 205],
  WATCH: [176, 141, 51, 210],
  MEDIUM: [216, 117, 43, 215],
  HIGH: [209, 63, 50, 225],
  CRITICAL: [165, 21, 21, 240],
};

/** Neutral monochrome point for assets without a risk tier. */
export const TRANSFORMER_RGBA: RGBAColor = [111, 111, 106, 230];
/** Interface selection — information blue, never a risk color. */
export const SELECTED_RGBA: RGBAColor = [46, 103, 199, 255];
/** Inspection routes use information blue. */
export const ROUTE_RGBA: RGBAColor = [46, 103, 199, 230];
/** Neutral outline for unselected map features. */
export const NEUTRAL_OUTLINE_RGBA: RGBAColor = [10, 10, 10, 150];

export function riskTierRgba(tier: RiskTier | null | undefined): RGBAColor {
  return tier ? RISK_TIER_RGBA[tier] : TRANSFORMER_RGBA;
}

/** Map score [0,100] to an interpolated risk fill (low green → critical red). */
export function riskScoreRgba(score: number | null | undefined, alpha = 205): RGBAColor {
  if (score == null) return [111, 111, 106, 120];
  const t = Math.max(0, Math.min(1, score / 100));
  const r = Math.round(75 + t * (209 - 75));
  const g = Math.round(139 - t * (139 - 63));
  const b = Math.round(103 - t * (103 - 50));
  return [r, g, b, alpha];
}

/** The bundled MapLibre demo style — a colorful consumer basemap we avoid. */
export const DEMO_TILES_STYLE_URL = "https://demotiles.maplibre.org/style.json";

const CARTO_ATTRIBUTION =
  '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>';

/**
 * A desaturated, monochrome infrastructure basemap. Uses CARTO's neutral gray
 * raster tiles with muted labels, on a themed background. Selection and risk
 * color come exclusively from the deck.gl operational layers above it.
 */
export function monochromeMapStyle(theme: "light" | "dark" = "dark"): StyleSpecification {
  const variant = theme === "dark" ? "dark_all" : "light_all";
  const background = theme === "dark" ? "#080808" : "#F4F4F2";
  return {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: [
          `https://a.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}{ratio}.png`,
          `https://b.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}{ratio}.png`,
          `https://c.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}{ratio}.png`,
        ].map((t) => t.replace("{ratio}", "")),
        tileSize: 256,
        attribution: CARTO_ATTRIBUTION,
      },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": background } },
      { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 1 } },
    ],
  };
}

/**
 * Resolve a configured style into the renderer input. When the configured value
 * is empty or the colorful MapLibre demo style, fall back to the monochrome
 * operational basemap so the chrome stays disciplined.
 */
export function resolveMapStyle(
  styleUrl: string | undefined,
  theme: "light" | "dark" = "dark"
): string | StyleSpecification {
  if (!styleUrl || styleUrl === DEMO_TILES_STYLE_URL) return monochromeMapStyle(theme);
  return styleUrl;
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
