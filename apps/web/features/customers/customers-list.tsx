"use client";

import type { Customer } from "@gridtrace/contracts";
import { RiskBadge } from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";
import { useGlobalFilters } from "@/lib/use-filters";

export function CustomersList() {
  const api = useApi();
  const router = useRouter();
  const { filters } = useGlobalFilters();
  const query = useQuery(
    api.customers.list({
      page: 1,
      page_size: 100,
      min_risk: filters.minRisk,
      tier: filters.tier,
    })
  );

  const columns = useMemo<ColumnDef<Customer, unknown>[]>(
    () => [
      { accessorKey: "external_ref", header: "Metering point" },
      { accessorKey: "customer_type", header: "Type" },
      { accessorKey: "region_id", header: "Region" },
      { accessorKey: "tariff_type", header: "Tariff" },
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
      <PageHeader
        title="Metering points"
        description="Risk-ranked metering points. Indicators are advisory and require human inspection."
      />
      <div className="space-y-4 p-6">
        <FilterBar showDateRange={false} />
        <QueryBoundary query={query} isEmpty={(p) => p.items.length === 0}>
          {(page) => (
            <DataTable
              columns={columns}
              data={page.items}
              initialSorting={[{ id: "risk_score", desc: true }]}
              getRowId={(row) => row.id}
              onRowClick={(row) => router.push(`/customers/${row.id}`)}
            />
          )}
        </QueryBoundary>
      </div>
    </div>
  );
}
