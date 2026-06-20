"use client";

import type { Customer } from "@gridtrace/contracts";
import { RiskBadge } from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";

// HIGH risk starts at 70 — everything at or above this is "flagged for review".
const FLAGGED_MIN_RISK = 70;

export function FlaggedReview() {
  const api = useApi();
  const router = useRouter();
  const query = useQuery(
    api.customers.list({ page: 1, page_size: 100, min_risk: FLAGGED_MIN_RISK })
  );

  const columns = useMemo<ColumnDef<Customer, unknown>[]>(
    () => [
      { accessorKey: "external_ref", header: "Customer" },
      { accessorKey: "customer_type", header: "Type" },
      { accessorKey: "region_id", header: "Region" },
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
        title="Flagged for review"
        description="High and critical-risk customers prioritized for inspection. Indicators are advisory and require on-site human confirmation."
      />
      <div className="space-y-4 p-6">
        <QueryBoundary
          query={query}
          isEmpty={(p) => p.items.length === 0}
          emptyTitle="No flagged customers in range"
        >
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
