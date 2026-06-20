"use client";

import type { RiskPointFeature } from "@gridtrace/maps";
import { RiskBadge } from "@gridtrace/ui";

export interface MapTooltipProps {
  feature: RiskPointFeature | null;
  x: number;
  y: number;
}

function num(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatKwh(value: number): string {
  return `${Math.round(value).toLocaleString()} kWh/yr`;
}

function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function MapTooltip({ feature, x, y }: MapTooltipProps) {
  if (!feature) return null;

  const props = feature.properties;
  const baseline = num(props.baseline_annual_kwh);
  const smartMeter = num(props.street_smartmeter_perc);
  const riskScore = num(props.risk_score);
  const riskTier = props.risk_tier ?? null;
  const label = props.external_ref ?? props.name ?? props.entity_id ?? "—";

  return (
    <div
      className="pointer-events-none absolute z-20 max-w-[16rem] rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-lg"
      style={{ left: x + 12, top: y + 12 }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-medium">{label}</span>
        {riskTier && riskScore != null ? (
          <RiskBadge tier={riskTier} score={riskScore} showScore={false} />
        ) : null}
      </div>
      <dl className="mt-1.5 space-y-0.5 text-muted-foreground">
        {baseline != null ? (
          <div className="flex justify-between gap-3">
            <dt>Baseline</dt>
            <dd className="font-medium tabular-nums text-foreground">{formatKwh(baseline)}</dd>
          </div>
        ) : null}
        {smartMeter != null ? (
          <div className="flex justify-between gap-3">
            <dt>Smart Meter Coverage</dt>
            <dd className="font-medium tabular-nums text-foreground">{formatPercent(smartMeter)}</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
