import { z } from "zod";
import { RISK_TIERS } from "@gridtrace/config";

const riskTierLabels = RISK_TIERS.map((t) => t.label) as [string, ...string[]];

export const dateRangeSchema = z.object({
  from: z.string().datetime({ offset: true }).optional(),
  to: z.string().datetime({ offset: true }).optional(),
});
export type DateRange = z.infer<typeof dateRangeSchema>;

/** Global filter schema persisted in URL search params. */
export const globalFiltersSchema = z.object({
  regionId: z.string().optional(),
  minRisk: z.coerce.number().min(0).max(100).optional(),
  tier: z.enum(riskTierLabels).optional(),
  from: z.string().optional(),
  to: z.string().optional(),
  selected: z.string().optional(),
});
export type GlobalFilters = z.infer<typeof globalFiltersSchema>;

/** Serialize filters to URLSearchParams (omitting empty values). */
export function filtersToSearchParams(filters: Partial<GlobalFilters>): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  return params;
}

export function filtersFromSearchParams(
  params: URLSearchParams | Record<string, string | undefined>
): GlobalFilters {
  const raw =
    params instanceof URLSearchParams ? Object.fromEntries(params.entries()) : params;
  return globalFiltersSchema.parse(raw);
}
