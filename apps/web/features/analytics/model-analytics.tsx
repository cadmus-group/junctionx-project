"use client";

import {
  CalibrationChart,
  PrecisionRecallChart,
  precisionRecallFromModel,
  RiskDistributionChart,
  type CalibrationPoint,
} from "@gridtrace/charts";
import type { ModelRegistryEntry } from "@gridtrace/contracts";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";

function calibrationFromModel(entry: ModelRegistryEntry): CalibrationPoint[] {
  const skew = entry.metrics.brier ?? 0.1;
  return Array.from({ length: 11 }, (_, i) => {
    const predicted = i / 10;
    const observed = Math.max(0, Math.min(1, predicted - skew * (predicted - 0.5)));
    return { predicted, observed };
  });
}

export function ModelAnalytics() {
  const api = useApi();
  const modelsQuery = useQuery(api.models.list());
  const summaryQuery = useQuery(api.dashboard.summary());

  const columns = useMemo<ColumnDef<ModelRegistryEntry, unknown>[]>(
    () => [
      { accessorKey: "model_version", header: "Model" },
      { accessorKey: "feature_version", header: "Features" },
      { accessorKey: "algorithm", header: "Algorithm" },
      {
        accessorKey: "metrics",
        header: "PR-AUC",
        cell: ({ row }) => row.original.metrics.pr_auc.toFixed(2),
      },
      {
        id: "precision_at_k",
        header: "P@k",
        cell: ({ row }) =>
          `${row.original.metrics.precision_at_k.toFixed(2)} @ ${row.original.metrics.k}`,
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) =>
          row.original.is_active ? (
            <Badge variant="success">Active</Badge>
          ) : (
            <Badge variant="secondary">Archived</Badge>
          ),
      },
    ],
    []
  );

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Model Analytics"
        description="Detection performance, calibration, and the model registry."
      />
      <div className="space-y-4 p-6">
        <QueryBoundary query={modelsQuery} isEmpty={(m) => m.length === 0}>
          {(models) => {
            const active = models.find((m) => m.is_active) ?? models[0]!;
            return (
              <>
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  <Card>
                    <CardHeader>
                      <CardTitle>Precision–recall</CardTitle>
                      <CardDescription>
                        Indicative shape from PR-AUC {active.metrics.pr_auc.toFixed(2)} ·{" "}
                        {active.model_version}. Full curve pending model export.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <PrecisionRecallChart
                        points={precisionRecallFromModel(active)}
                        height={260}
                        ariaLabel={`Precision–recall curve for model ${active.model_version}, PR-AUC ${active.metrics.pr_auc.toFixed(2)}.`}
                      />
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle>Calibration</CardTitle>
                      <CardDescription>
                        Indicative reliability from the Brier score. Full curve pending model export.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <CalibrationChart
                        points={calibrationFromModel(active)}
                        height={260}
                        ariaLabel={`Calibration reliability curve for model ${active.model_version}.`}
                      />
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle>Risk distribution</CardTitle>
                      <CardDescription>Scored population by tier.</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <QueryBoundary query={summaryQuery}>
                        {(summary) => (
                          <RiskDistributionChart
                            breakdown={summary.risk_tier_breakdown}
                            height={260}
                            ariaLabel="Scored metering points by risk tier."
                          />
                        )}
                      </QueryBoundary>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Model registry</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <DataTable columns={columns} data={models} getRowId={(m) => m.id} />
                  </CardContent>
                </Card>
              </>
            );
          }}
        </QueryBoundary>
      </div>
    </div>
  );
}
