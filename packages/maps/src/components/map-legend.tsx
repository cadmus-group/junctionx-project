"use client";

import type { RiskTier } from "@gridtrace/contracts";
import { RISK_TIER_RGBA, SELECTED_RGBA, TRANSFORMER_RGBA } from "../style";

const TIER_ORDER: RiskTier[] = ["LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL"];
const TIER_LABEL: Record<RiskTier, string> = {
  LOW: "Low",
  WATCH: "Watch",
  MEDIUM: "Medium",
  HIGH: "High",
  CRITICAL: "Critical",
};

function rgba(c: readonly number[]): string {
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${(c[3] ?? 255) / 255})`;
}

export interface MapLegendProps {
  title?: string;
  showTransformers?: boolean;
  className?: string;
}

export function MapLegend({
  title = "Risk score",
  showTransformers = true,
  className,
}: MapLegendProps) {
  return (
    <div
      className={
        className ??
        "pointer-events-none absolute bottom-4 left-4 z-10 rounded-sm border border-border bg-surface p-3 text-xs text-foreground"
      }
    >
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <div className="flex flex-col gap-1">
        {TIER_ORDER.map((tier) => (
          <div key={tier} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-[1px]"
              style={{ backgroundColor: rgba(RISK_TIER_RGBA[tier]) }}
            />
            <span className="text-muted-foreground">{TIER_LABEL[tier]}</span>
          </div>
        ))}
        <div className="mt-1 flex items-center gap-2 border-t border-border pt-1">
          <span
            className="h-2.5 w-2.5 rounded-[1px] ring-2 ring-offset-1 ring-offset-surface"
            style={{ backgroundColor: "transparent", boxShadow: `0 0 0 2px ${rgba(SELECTED_RGBA)}` }}
          />
          <span className="text-muted-foreground">Selected</span>
        </div>
        {showTransformers ? (
          <div className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-[1px]"
              style={{ backgroundColor: rgba(TRANSFORMER_RGBA) }}
            />
            <span className="text-muted-foreground">Transformer (no tier)</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
