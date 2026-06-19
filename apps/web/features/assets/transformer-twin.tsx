"use client";

import { EnergyWaterfallChart } from "@gridtrace/charts";
import type { AssetCustomerSummary } from "@gridtrace/contracts";
import type { Currency } from "@gridtrace/config";
import { formatCurrency, formatEnergyKwh, formatPercent } from "@gridtrace/domain";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  KpiCard,
  RiskBadge,
} from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Activity, Euro, Gauge, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";

export function TransformerTwin({ id }: { id: string }) {
  const api = useApi();
  const router = useRouter();
  const reconQuery = useQuery(api.assets.reconciliation(id));
  const customersQuery = useQuery(api.assets.customers(id, { page: 1, page_size: 50 }));

  const columns = useMemo<ColumnDef<AssetCustomerSummary, unknown>[]>(
    () => [
      { accessorKey: "external_ref", header: "Customer" },
      { accessorKey: "customer_type", header: "Type" },
      {
        accessorKey: "estimated_loss_kwh",
        header: "Est. loss",
        cell: ({ getValue }) => {
          const v = getValue() as number | null;
          return v != null ? formatEnergyKwh(v) : "—";
        },
      },
      {
        accessorKey: "risk_score",
        header: "Risk",
        cell: ({ row }) =>
          row.original.risk_tier ? (
            <RiskBadge tier={row.original.risk_tier} score={row.original.risk_score ?? undefined} />
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
    ],
    []
  );

  return (
    <div className="flex flex-col">
      <QueryBoundary query={reconQuery}>
        {(recon) => {
          const currency = recon.currency as Currency;
          return (
            <>
              <PageHeader
                title={recon.name}
                description={`Digital twin · energy reconciliation for ${recon.transformer_id}`}
                actions={<RiskBadge tier={recon.risk_tier} score={recon.risk_score} />}
              />
              <div className="space-y-4 p-6">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <KpiCard
                    label="Energy input"
                    value={formatEnergyKwh(recon.energy_input_kwh)}
                    icon={Zap}
                  />
                  <KpiCard
                    label="Metered output"
                    value={formatEnergyKwh(recon.metered_output_kwh)}
                    icon={Gauge}
                  />
                  <KpiCard
                    label="Unexplained loss"
                    value={formatEnergyKwh(recon.unexplained_loss_kwh)}
                    icon={Activity}
                    hint={formatPercent(recon.unexplained_loss_ratio)}
                  />
                  <KpiCard
                    label="Estimated value"
                    value={formatCurrency(recon.estimated_loss_value, currency)}
                    icon={Euro}
                  />
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Energy reconciliation</CardTitle>
                    <CardDescription>
                      Input → metered output → estimated technical loss → unexplained residual
                      (kWh).
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <EnergyWaterfallChart reconciliation={recon} height={320} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Downstream customers</CardTitle>
                    <CardDescription>
                      {recon.customer_count} metered customers feed from this transformer.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <QueryBoundary
                      query={customersQuery}
                      isEmpty={(p) => p.items.length === 0}
                      emptyTitle="No downstream customers"
                    >
                      {(page) => (
                        <DataTable
                          columns={columns}
                          data={page.items}
                          initialSorting={[{ id: "risk_score", desc: true }]}
                          getRowId={(row) => row.customer_id}
                          onRowClick={(row) => router.push(`/customers/${row.customer_id}`)}
                        />
                      )}
                    </QueryBoundary>
                  </CardContent>
                </Card>
              </div>
            </>
          );
        }}
      </QueryBoundary>
    </div>
  );
}
