import type { RiskExplanation } from "@gridtrace/contracts";
import { ArrowDown, ArrowUp } from "lucide-react";

export function ExplanationList({ explanations }: { explanations: RiskExplanation[] }) {
  const max = Math.max(...explanations.map((e) => Math.abs(e.contribution)), 0.0001);
  return (
    <ul className="space-y-3">
      {explanations.map((e) => {
        const increases = e.direction === "increases";
        const width = `${Math.round((Math.abs(e.contribution) / max) * 100)}%`;
        return (
          <li key={e.feature} className="space-y-1">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="flex items-center gap-1.5 text-foreground">
                {increases ? (
                  <ArrowUp className="h-3.5 w-3.5 text-danger" />
                ) : (
                  <ArrowDown className="h-3.5 w-3.5 text-success" />
                )}
                {e.label}
              </span>
              <span className="tabular-nums text-muted-foreground">
                {increases ? "+" : "−"}
                {Math.abs(Math.round(e.contribution * 100))}%
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={increases ? "h-full bg-danger" : "h-full bg-success"}
                style={{ width }}
              />
            </div>
            {e.detail ? <p className="text-xs text-muted-foreground">{e.detail}</p> : null}
          </li>
        );
      })}
    </ul>
  );
}
