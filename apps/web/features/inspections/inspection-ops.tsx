"use client";

import type { InspectionMission, InspectionQueueItem } from "@gridtrace/contracts";
import type { Currency } from "@gridtrace/config";
import { formatCurrency, formatEnergyKwh } from "@gridtrace/domain";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  RiskBadge,
} from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { ClipboardPlus } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { DataTable } from "@/components/data-table";
import { InspectionStatusBadge } from "@/components/inspection-status-badge";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";
import { AddToMissionDialog } from "./add-to-mission-dialog";
import { CreateMissionForm } from "./create-mission-form";

export function InspectionOps() {
  const api = useApi();
  const queueQuery = useQuery(api.inspections.queue({ page: 1, page_size: 50 }));
  const missionsQuery = useQuery(api.inspections.missions());

  const columns = useMemo<ColumnDef<InspectionQueueItem, unknown>[]>(
    () => [
      {
        accessorKey: "inspection_priority",
        header: "Priority",
        cell: ({ getValue }) => (
          <span className="font-semibold tabular-nums">{String(getValue())}</span>
        ),
      },
      {
        accessorKey: "external_ref",
        header: "Customer",
        cell: ({ row }) => (
          <Link
            href={`/customers/${row.original.customer_id}`}
            className="text-foreground hover:text-primary"
          >
            {row.original.external_ref}
          </Link>
        ),
      },
      { accessorKey: "region_name", header: "Region" },
      {
        accessorKey: "risk_score",
        header: "Risk",
        cell: ({ row }) => (
          <RiskBadge
            tier={row.original.risk_tier as never}
            score={row.original.risk_score}
          />
        ),
      },
      {
        accessorKey: "estimated_loss_kwh",
        header: "Est. loss",
        cell: ({ getValue }) => formatEnergyKwh(getValue() as number),
      },
      {
        accessorKey: "estimated_loss_value",
        header: "Value",
        cell: ({ row }) =>
          formatCurrency(row.original.estimated_loss_value, row.original.currency as Currency),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <AddToMissionDialog
            customerId={row.original.customer_id}
            recommendedAction={row.original.recommended_action}
            trigger={
              <Button variant="ghost" size="sm">
                <ClipboardPlus className="h-4 w-4" />
                Add
              </Button>
            }
          />
        ),
      },
    ],
    []
  );

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Inspection Operations"
        description="Prioritized inspection queue and field missions."
        actions={<CreateMissionForm />}
      />
      <div className="space-y-4 p-6">
        <Card>
          <CardHeader>
            <CardTitle>Missions</CardTitle>
            <CardDescription>Active and planned field missions.</CardDescription>
          </CardHeader>
          <CardContent>
            <QueryBoundary
              query={missionsQuery}
              isEmpty={(p) => p.items.length === 0}
              emptyTitle="No missions yet"
              emptyDescription="Create a mission to start grouping inspection cases."
            >
              {(page) => <MissionGrid missions={page.items} />}
            </QueryBoundary>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Inspection queue</CardTitle>
            <CardDescription>
              Ranked by model inspection priority. Confirmation always requires a field visit.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <QueryBoundary query={queueQuery} isEmpty={(p) => p.items.length === 0}>
              {(page) => (
                <DataTable
                  columns={columns}
                  data={page.items}
                  initialSorting={[{ id: "inspection_priority", desc: true }]}
                  getRowId={(row) => row.customer_id}
                />
              )}
            </QueryBoundary>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MissionGrid({ missions }: { missions: InspectionMission[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {missions.map((m) => (
        <Link
          key={m.id}
          href={`/inspections/${m.id}`}
          className="rounded-lg border border-border bg-surface p-4 transition-colors hover:border-primary/50"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium">{m.name}</span>
            <InspectionStatusBadge status={m.status} />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {m.case_count} cases · {formatCurrency(m.estimated_total_value, m.currency as Currency)}
          </p>
        </Link>
      ))}
    </div>
  );
}
