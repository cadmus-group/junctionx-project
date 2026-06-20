import { z } from "zod";

export * from "./design-tokens";

/**
 * Shared non-secret configuration: public env schema, risk labels, map defaults,
 * demo flags, supported locales and currencies. No secrets belong here.
 */

export const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default("http://localhost:8003"),
  NEXT_PUBLIC_MAP_STYLE_URL: z
    .string()
    .url()
    .default("https://demotiles.maplibre.org/style.json"),
  NEXT_PUBLIC_DEMO_MODE: z
    .string()
    .optional()
    .default("false")
    .transform((v) => v === "true" || v === "1"),
});

export type PublicEnv = z.infer<typeof publicEnvSchema>;

export function parsePublicEnv(env: Record<string, string | undefined>): PublicEnv {
  return publicEnvSchema.parse(env);
}

/** Risk tiers — must mirror backend core_formulas.risk_tiers exactly. */
export const RISK_TIERS = [
  { label: "LOW", min: 0, max: 29 },
  { label: "WATCH", min: 30, max: 49 },
  { label: "MEDIUM", min: 50, max: 69 },
  { label: "HIGH", min: 70, max: 84 },
  { label: "CRITICAL", min: 85, max: 100 },
] as const;

export type RiskTierLabel = (typeof RISK_TIERS)[number]["label"];

export const RISK_LABELS: Record<RiskTierLabel, string> = {
  LOW: "Low",
  WATCH: "Watch",
  MEDIUM: "Medium",
  HIGH: "High",
  CRITICAL: "Critical",
};

/** Map defaults centered on the seeded demo operator (Netherlands). */
export const MAP_DEFAULTS = {
  center: [4.9041, 52.3676] as [number, number],
  zoom: 11,
  minZoom: 4,
  maxZoom: 18,
  /** Below this zoom, do not render individual customer points. */
  customerDetailMinZoom: 13,
} as const;

export const DEMO_FLAGS = {
  defaultDemoMode: false,
  cachedGeoJsonPath: "/demo",
} as const;

export const SUPPORTED_LOCALES = ["en-US", "nl-NL"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const SUPPORTED_CURRENCIES = ["EUR", "USD"] as const;
export type Currency = (typeof SUPPORTED_CURRENCIES)[number];
