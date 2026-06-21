"use client";

import type { RiskTier } from "@gridtrace/contracts";
import type { RiskPointFeature } from "@gridtrace/maps";
import { cn, RiskBadge } from "@gridtrace/ui";

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

const TIER_ACCENT: Record<RiskTier, string> = {
  LOW: "bg-risk-low",
  WATCH: "bg-risk-watch",
  MEDIUM: "bg-risk-medium",
  HIGH: "bg-risk-high",
  CRITICAL: "bg-risk-critical",
};

const TIER_TEXT: Record<RiskTier, string> = {
  LOW: "text-risk-low",
  WATCH: "text-risk-watch",
  MEDIUM: "text-risk-medium",
  HIGH: "text-risk-high",
  CRITICAL: "text-risk-critical",
};

export function MapTooltip({ feature, x, y }: MapTooltipProps) {
  if (!feature) return null;

  const props = feature.properties;
  const baseline = num(props.baseline_annual_kwh);
  const smartMeter = num(props.street_smartmeter_perc);
  const riskScore = num(props.risk_score);
  const riskTier = props.risk_tier ?? null;
  const label = String(props.external_ref ?? props.name ?? props.entity_id ?? "—");
  const entityType = props.entity_type === "transformer" ? "Transformer" : "Metering point";
  const hasDetails = baseline != null || smartMeter != null;

  return (
    <div
      className="pointer-events-none absolute z-20 w-60 overflow-hidden rounded-md border border-border bg-surface-elevated text-xs shadow-xl"
      style={{ left: x + 14, top: y + 14 }}
    >
      {/* Risk-tier accent strip — instant signal */}
      <div className={cn("h-1 w-full", riskTier ? TIER_ACCENT[riskTier] : "bg-border")} />

      {/* Header */}
      <div className="px-3 pb-2 pt-2.5">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {entityType}
        </p>
        <p className="truncate text-sm font-semibold text-foreground">{label}</p>
      </div>

      {/* Risk score — the headline */}
      {riskScore != null && riskTier ? (
        <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-2">
          <div className="flex items-baseline gap-1">
            <span className={cn("text-2xl font-bold tabular-nums", TIER_TEXT[riskTier])}>
              {Math.round(riskScore)}
            </span>
            <span className="text-[10px] text-muted-foreground">/ 100</span>
          </div>
          <RiskBadge tier={riskTier} score={riskScore} showScore={false} />
        </div>
      ) : null}

      {/* Supporting detail */}
      {hasDetails ? (
        <dl className="space-y-1 border-t border-border px-3 py-2 text-muted-foreground">
          {baseline != null ? (
            <div className="flex justify-between gap-3">
              <dt>Baseline</dt>
              <dd className="font-medium tabular-nums text-foreground">{formatKwh(baseline)}</dd>
            </div>
          ) : null}
          {smartMeter != null ? (
            <div className="flex justify-between gap-3">
              <dt>Smart meter</dt>
              <dd className="font-medium tabular-nums text-foreground">
                {formatPercent(smartMeter)}
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}
    </div>
  );
}
