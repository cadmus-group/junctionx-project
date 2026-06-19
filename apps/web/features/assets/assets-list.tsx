"use client";

import type { GridAsset } from "@gridtrace/contracts";
import { RiskBadge } from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";

export function AssetsList() {
  const api = useApi();
  const router = useRouter();
  const query = useQuery(api.assets.list({ page: 1, page_size: 50, asset_type: "transformer" }));

  const columns = useMemo<ColumnDef<GridAsset, unknown>[]>(
    () => [
      { accessorKey: "name", header: "Transformer" },
      { accessorKey: "external_id", header: "External ID" },
      { accessorKey: "voltage_level", header: "Voltage" },
      {
        accessorKey: "capacity_kva",
        header: "Capacity (kVA)",
        cell: ({ getValue }) => <span className="tabular-nums">{String(getValue() ?? "—")}</span>,
      },
      {
        accessorKey: "risk_score",
        header: "Risk",
        sortingFn: (a, b) => (a.original.risk_score ?? 0) - (b.original.risk_score ?? 0),
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
        title="Assets"
        description="Distribution transformers ranked by unexplained-loss risk."
      />
      <div className="p-6">
        <QueryBoundary query={query} isEmpty={(p) => p.items.length === 0}>
          {(page) => (
            <DataTable
              columns={columns}
              data={page.items}
              initialSorting={[{ id: "risk_score", desc: true }]}
              getRowId={(row) => row.id}
              onRowClick={(row) => router.push(`/assets/transformers/${row.id}`)}
            />
          )}
        </QueryBoundary>
      </div>
    </div>
  );
}
