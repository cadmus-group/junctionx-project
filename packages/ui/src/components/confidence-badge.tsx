import { cn } from "../lib/cn";

export interface ConfidenceBadgeProps {
  /** Confidence in [0,1]. */
  confidence: number;
  className?: string;
}

export function confidenceLabel(confidence: number): "Low" | "Moderate" | "High" {
  if (confidence >= 0.75) return "High";
  if (confidence >= 0.5) return "Moderate";
  return "Low";
}

export function ConfidenceBadge({ confidence, className }: ConfidenceBadgeProps) {
  const clamped = Math.max(0, Math.min(1, confidence));
  const label = confidenceLabel(clamped);
  const pct = Math.round(clamped * 100);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border border-border bg-surface px-2 py-0.5 text-[11px] font-semibold text-foreground",
        className
      )}
      title={`Model confidence: ${pct}%`}
    >
      <span className="text-muted-foreground">Confidence</span>
      <span
        className={cn("font-semibold", {
          "text-danger": label === "Low",
          "text-warning": label === "Moderate",
          "text-success": label === "High",
        })}
      >
        {label}
      </span>
      <span className="tabular-nums text-muted-foreground">{pct}%</span>
    </span>
  );
}
