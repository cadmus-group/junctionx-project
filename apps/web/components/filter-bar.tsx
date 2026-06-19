"use client";

import { RISK_TIERS } from "@gridtrace/config";
import { Label, Select } from "@gridtrace/ui";
import { DEMO_REGIONS } from "@gridtrace/testing/data";
import { useGlobalFilters } from "@/lib/use-filters";
import { DateRangePicker } from "./date-range-picker";

export interface FilterBarProps {
  showRegion?: boolean;
  showTier?: boolean;
  showDateRange?: boolean;
}

export function FilterBar({
  showRegion = true,
  showTier = true,
  showDateRange = true,
}: FilterBarProps) {
  const { filters, setFilters } = useGlobalFilters();

  return (
    <div className="flex flex-wrap items-end gap-3">
      {showRegion ? (
        <div className="space-y-1">
          <Label htmlFor="region" className="text-xs text-muted-foreground">
            Region
          </Label>
          <Select
            id="region"
            className="h-8 w-44"
            value={filters.regionId ?? ""}
            onChange={(e) => setFilters({ regionId: e.target.value || undefined })}
          >
            <option value="">All regions</option>
            {DEMO_REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </Select>
        </div>
      ) : null}

      {showTier ? (
        <div className="space-y-1">
          <Label htmlFor="tier" className="text-xs text-muted-foreground">
            Risk tier
          </Label>
          <Select
            id="tier"
            className="h-8 w-36"
            value={filters.tier ?? ""}
            onChange={(e) => setFilters({ tier: (e.target.value || undefined) as never })}
          >
            <option value="">All tiers</option>
            {RISK_TIERS.map((t) => (
              <option key={t.label} value={t.label}>
                {t.label}
              </option>
            ))}
          </Select>
        </div>
      ) : null}

      {showDateRange ? (
        <DateRangePicker
          from={filters.from}
          to={filters.to}
          onChange={(range) => setFilters(range)}
        />
      ) : null}
    </div>
  );
}
