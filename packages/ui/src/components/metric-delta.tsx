import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { cn } from "../lib/cn";

export interface MetricDeltaProps {
  /** Fractional change, e.g. 0.12 for +12%. */
  delta: number;
  /** When true, an increase is bad (e.g. losses). Defaults to false. */
  invert?: boolean;
  formatted?: string;
  className?: string;
}

export function MetricDelta({ delta, invert = false, formatted, className }: MetricDeltaProps) {
  const isFlat = Math.abs(delta) < 0.0005;
  const isUp = delta > 0;
  const good = isFlat ? false : invert ? !isUp : isUp;
  const Icon = isFlat ? ArrowRight : isUp ? ArrowUpRight : ArrowDownRight;
  const sign = isUp ? "+" : "";
  const label = formatted ?? `${sign}${(delta * 100).toFixed(1)}%`;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        isFlat ? "text-muted-foreground" : good ? "text-success" : "text-danger",
        className
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}
