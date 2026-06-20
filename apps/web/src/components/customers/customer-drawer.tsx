"use client";

import type { PeerComparisonPoint } from "@gridtrace/contracts";
import { formatEnergyKwh, formatPercent } from "@gridtrace/domain";
import { Badge } from "@gridtrace/ui";

const RECENT_DAYS = 14;
/** Consumption above 50% of street baseline triggers the deviation warning. */
const DEVIATION_THRESHOLD = 0.5;

export interface SpatialContextData {
  baseline_annual_kwh?: number | null;
  street_smartmeter_perc?: number | null;
  recent_annualized_kwh?: number | null;
  baseline_deviation_ratio?: number | null;
}

export interface SpatialContextSectionProps {
  spatialContext?: SpatialContextData | null;
  /** Fallback when spatial_context is absent from the API. */
  baselineAnnualKwh?: number | null;
  peerComparison?: PeerComparisonPoint[];
  showHeading?: boolean;
  className?: string;
}

function recentAnnualizedFromPeers(peerComparison: PeerComparisonPoint[]): number | null {
  if (!peerComparison.length) return null;
  const recent = peerComparison.slice(-RECENT_DAYS);
  const dailyAvg = recent.reduce((sum, p) => sum + p.customer_kwh, 0) / recent.length;
  return dailyAvg * 365;
}

export function SpatialContextSection({
  spatialContext,
  baselineAnnualKwh,
  peerComparison = [],
  showHeading = true,
  className,
}: SpatialContextSectionProps) {
  const baseline =
    spatialContext?.baseline_annual_kwh ?? baselineAnnualKwh ?? null;
  const smartMeter = spatialContext?.street_smartmeter_perc ?? null;
  const recentAnnualized =
    spatialContext?.recent_annualized_kwh ??
    recentAnnualizedFromPeers(peerComparison);
  const deviationRatio =
    spatialContext?.baseline_deviation_ratio ??
    (baseline != null &&
    baseline > 0 &&
    recentAnnualized != null
      ? (recentAnnualized - baseline) / baseline
      : null);

  const showWarning =
    deviationRatio != null && deviationRatio > DEVIATION_THRESHOLD;
  const hasData =
    baseline != null || smartMeter != null || recentAnnualized != null;

  return (
    <section className={className ?? "mt-4 border-t border-border pt-4"}>
      {showHeading ? (
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Spatial Context
        </h3>
      ) : null}
      {!hasData ? (
        <p className="mt-2 text-sm text-muted-foreground">
          No Dutch Energy street baseline assigned (zipcode missing or not ingested).
        </p>
      ) : (
        <dl className={showHeading ? "mt-2 space-y-2 text-sm" : "space-y-2 text-sm"}>
          <div className="flex items-center justify-between gap-2">
            <dt className="text-muted-foreground">Street baseline</dt>
            <dd className="font-medium tabular-nums">
              {baseline != null ? formatEnergyKwh(baseline) : "—"}
            </dd>
          </div>
          {smartMeter != null ? (
            <div className="flex items-center justify-between gap-2">
              <dt className="text-muted-foreground">Smart meter coverage</dt>
              <dd className="font-medium tabular-nums">{Math.round(smartMeter)}%</dd>
            </div>
          ) : null}
          {recentAnnualized != null ? (
            <div className="flex items-center justify-between gap-2">
              <dt className="text-muted-foreground">Recent (annualized)</dt>
              <dd className="font-medium tabular-nums">
                {formatEnergyKwh(recentAnnualized)}
              </dd>
            </div>
          ) : null}
          {deviationRatio != null ? (
            <div className="flex items-center justify-between gap-2">
              <dt className="text-muted-foreground">Baseline deviation</dt>
              <dd className="font-medium tabular-nums">
                {deviationRatio >= 0 ? "+" : ""}
                {formatPercent(deviationRatio)}
              </dd>
            </div>
          ) : null}
        </dl>
      )}
      {showWarning ? (
        <Badge variant="warning" className="mt-3">
          High Deviation from Street Baseline
        </Badge>
      ) : null}
    </section>
  );
}
