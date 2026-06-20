"use client";

import type { InspectionCase } from "@gridtrace/contracts";
import type { Currency } from "@gridtrace/config";
import { formatCurrency, formatDateTime } from "@gridtrace/domain";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  Label,
} from "@gridtrace/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/client";
import { InspectionStatusBadge } from "@/components/inspection-status-badge";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";
import { appendCaseToCache, caseListKey } from "./case-cache";
import { SubmitOutcomeForm } from "./submit-outcome-form";

export function MissionDetail({ id }: { id: string }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const missionsQuery = useQuery(api.inspections.missions());
  const [customerId, setCustomerId] = useState("");

  const casesQuery = useQuery<InspectionCase[]>({
    queryKey: caseListKey(id),
    queryFn: () => queryClient.getQueryData<InspectionCase[]>(caseListKey(id)) ?? [],
    initialData: () => queryClient.getQueryData<InspectionCase[]>(caseListKey(id)) ?? [],
    staleTime: Infinity,
  });

  const addCase = useMutation({
    mutationFn: (cust: string) =>
      api.inspectionMutations.addCase(id, {
        customer_id: cust,
        recommended_action: "On-site inspection to confirm and explain unexplained consumption",
      }),
    onSuccess: (created) => {
      appendCaseToCache(queryClient, id, created);
      setCustomerId("");
    },
  });

  return (
    <div className="flex flex-col">
      <QueryBoundary query={missionsQuery}>
        {(page) => {
          const mission = page.items.find((m) => m.id === id);
          if (!mission) {
            return (
              <div className="p-6">
                <EmptyState
                  title="Mission not found"
                  description="This mission may have been created in another session."
                  action={
                    <Button asChild variant="outline" size="sm">
                      <Link href="/inspections">Back to inspections</Link>
                    </Button>
                  }
                />
              </div>
            );
          }
          return (
            <>
              <PageHeader
                title={mission.name}
                description={`${mission.case_count} cases · created ${formatDateTime(mission.created_at)}`}
                actions={<InspectionStatusBadge status={mission.status} />}
              />
              <div className="space-y-4 p-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Mission summary</CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                    <Stat label="Region" value={mission.region_id ?? "—"} />
                    <Stat
                      label="Scheduled"
                      value={mission.scheduled_date ? mission.scheduled_date.slice(0, 10) : "—"}
                    />
                    <Stat
                      label="Estimated value"
                      value={formatCurrency(
                        mission.estimated_total_value,
                        mission.currency as Currency
                      )}
                    />
                    <Stat label="Team" value={mission.assigned_team_id ?? "Unassigned"} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Cases</CardTitle>
                    <CardDescription>
                      Cases queued in this session. Record field-verified outcomes here.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-end gap-2">
                      <div className="space-y-1.5">
                        <Label htmlFor="add-case" className="text-xs text-muted-foreground">
                          Add case by customer ID
                        </Label>
                        <Input
                          id="add-case"
                          placeholder="cust-0001"
                          className="w-48"
                          value={customerId}
                          onChange={(e) => setCustomerId(e.target.value)}
                        />
                      </div>
                      <Button
                        size="sm"
                        disabled={!customerId || addCase.isPending}
                        onClick={() => addCase.mutate(customerId)}
                      >
                        Add case
                      </Button>
                    </div>

                    {casesQuery.data.length === 0 ? (
                      <EmptyState
                        title="No cases yet"
                        description="Add cases from the inspection queue or a customer investigation."
                      />
                    ) : (
                      <ul className="divide-y divide-border rounded-sm border border-border">
                        {casesQuery.data.map((c) => (
                          <li key={c.id} className="flex items-center justify-between gap-3 p-3">
                            <div>
                              <Link
                                href={`/customers/${c.customer_id}`}
                                className="text-sm font-medium hover:text-primary"
                              >
                                {c.customer_id}
                              </Link>
                              <p className="text-xs text-muted-foreground">
                                {c.recommended_action}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <InspectionStatusBadge status={c.status} />
                              <SubmitOutcomeForm
                                missionId={id}
                                inspectionCase={c}
                                trigger={
                                  <Button variant="outline" size="sm">
                                    <ClipboardCheck className="h-4 w-4" />
                                    Outcome
                                  </Button>
                                }
                              />
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
