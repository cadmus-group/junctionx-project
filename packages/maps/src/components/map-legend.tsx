"use client";

import type { RiskTier } from "@gridtrace/contracts";
import { RISK_TIER_RGBA } from "../style";

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
        "pointer-events-none absolute bottom-4 left-4 z-10 rounded-md border border-border bg-surface-elevated/90 p-3 text-xs text-foreground shadow-md backdrop-blur"
      }
    >
      <p className="mb-2 font-medium">{title}</p>
      <div className="flex flex-col gap-1">
        {TIER_ORDER.map((tier) => (
          <div key={tier} className="flex items-center gap-2">
            <span
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: rgba(RISK_TIER_RGBA[tier]) }}
            />
            <span className="text-muted-foreground">{TIER_LABEL[tier]}</span>
          </div>
        ))}
        {showTransformers ? (
          <div className="mt-1 flex items-center gap-2 border-t border-border pt-1">
            <span className="h-3 w-3 rounded-full ring-2 ring-white/70" style={{ backgroundColor: "rgba(56,189,248,0.9)" }} />
            <span className="text-muted-foreground">Transformer</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
