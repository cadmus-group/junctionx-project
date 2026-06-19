import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { Card, CardContent } from "./card";
import { MetricDelta } from "./metric-delta";

export interface KpiCardProps {
  label: string;
  value: ReactNode;
  unit?: string;
  icon?: LucideIcon;
  delta?: number;
  deltaInvert?: boolean;
  deltaFormatted?: string;
  hint?: string;
  className?: string;
}

export function KpiCard({
  label,
  value,
  unit,
  icon: Icon,
  delta,
  deltaInvert,
  deltaFormatted,
  hint,
  className,
}: KpiCardProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          {Icon ? <Icon className="h-4 w-4 text-muted-foreground" /> : null}
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl font-semibold tabular-nums text-foreground">{value}</span>
          {unit ? <span className="text-sm text-muted-foreground">{unit}</span> : null}
        </div>
        <div className="mt-1 flex items-center gap-2">
          {typeof delta === "number" ? (
            <MetricDelta delta={delta} invert={deltaInvert} formatted={deltaFormatted} />
          ) : null}
          {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
        </div>
      </CardContent>
    </Card>
  );
}
