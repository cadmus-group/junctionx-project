import type { RiskTier } from "@gridtrace/contracts";
import { cn } from "../lib/cn";

const TIER_STYLES: Record<RiskTier, string> = {
  LOW: "bg-risk-low/10 text-risk-low border-risk-low/35",
  WATCH: "bg-risk-watch/10 text-risk-watch border-risk-watch/35",
  MEDIUM: "bg-risk-medium/10 text-risk-medium border-risk-medium/35",
  HIGH: "bg-risk-high/10 text-risk-high border-risk-high/35",
  CRITICAL: "bg-risk-critical/12 text-risk-critical border-risk-critical/40",
};

const TIER_LABELS: Record<RiskTier, string> = {
  LOW: "Low",
  WATCH: "Watch",
  MEDIUM: "Medium",
  HIGH: "High",
  CRITICAL: "Critical",
};

export interface RiskBadgeProps {
  tier: RiskTier;
  score?: number;
  className?: string;
  showScore?: boolean;
}

export function RiskBadge({ tier, score, className, showScore = true }: RiskBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[11px] font-semibold",
        TIER_STYLES[tier],
        className
      )}
    >
      <span
        className={cn("h-1.5 w-1.5 rounded-full", {
          "bg-risk-low": tier === "LOW",
          "bg-risk-watch": tier === "WATCH",
          "bg-risk-medium": tier === "MEDIUM",
          "bg-risk-high": tier === "HIGH",
          "bg-risk-critical": tier === "CRITICAL",
        })}
      />
      {TIER_LABELS[tier]}
      {showScore && typeof score === "number" ? (
        <span className="tabular-nums opacity-80">{Math.round(score)}</span>
      ) : null}
    </span>
  );
}
