"use client";

import { ActualVsExpectedChart, PeerComparisonChart } from "@gridtrace/charts";
import type { RiskComponents } from "@gridtrace/contracts";
import type { Currency } from "@gridtrace/config";
import { formatCurrency, formatEnergyKwh, formatNumber, formatPercent } from "@gridtrace/domain";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ConfidenceBadge,
  RiskBadge,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import { ClipboardPlus, Info } from "lucide-react";
import { useApi } from "@/lib/client";
import { ExplanationList } from "@/components/explanation-list";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";
import { AddToMissionDialog } from "@/features/inspections/add-to-mission-dialog";
import { SpatialContextSection } from "@/src/components/customers/customer-drawer";

const COMPONENT_LABELS: Record<keyof RiskComponents, string> = {
  supervised_probability: "Supervised model",
  anomaly_score: "Anomaly detection",
  grid_imbalance_score: "Grid imbalance",
  peer_score: "Peer deviation",
  spatial_score: "Spatial context",
};

export function CustomerInvestigation({ id }: { id: string }) {
  const api = useApi();
  const profileQuery = useQuery(api.customers.riskProfile(id));

  return (
    <div className="flex flex-col">
      <QueryBoundary query={profileQuery}>
        {(profile) => {
          const { customer, risk, peer_comparison, spatial_context, loss_attribution_share, notes } = profile;
          const currency = risk.currency as Currency;
          return (
            <>
              <PageHeader
                title={customer.external_ref}
                description={`${customer.customer_type} · ${customer.region_id ?? "—"} · scored ${risk.scored_at.slice(0, 10)}`}
                actions={
                  <div className="flex items-center gap-2">
                    <ConfidenceBadge confidence={risk.confidence} />
                    <RiskBadge tier={risk.risk_tier} score={risk.risk_score} />
                    <AddToMissionDialog
                      customerId={customer.id}
                      riskScoreId={risk.id}
                      recommendedAction="On-site inspection to confirm and explain unexplained consumption"
                      trigger={
                        <Button size="sm">
                          <ClipboardPlus className="h-4 w-4" />
                          Add to inspection mission
                        </Button>
                      }
                    />
                  </div>
                }
              />
              <div className="grid grid-cols-1 gap-4 p-6 lg:grid-cols-3">
                <div className="space-y-4 lg:col-span-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Consumption vs expected</CardTitle>
                      <CardDescription>
                        Metered consumption against model-expected and peer-median usage (kWh).
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Tabs defaultValue="expected">
                        <TabsList>
                          <TabsTrigger value="expected">Actual vs expected</TabsTrigger>
                          <TabsTrigger value="peer">Peer comparison</TabsTrigger>
                        </TabsList>
                        <TabsContent value="expected">
                          <ActualVsExpectedChart points={peer_comparison} height={280} />
                        </TabsContent>
                        <TabsContent value="peer">
                          <PeerComparisonChart points={peer_comparison} height={280} />
                        </TabsContent>
                      </Tabs>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Why this score</CardTitle>
                      <CardDescription>
                        Leading contributors to the model&apos;s risk estimate.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ExplanationList explanations={risk.explanations} />
                    </CardContent>
                  </Card>
                </div>

                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Peer baseline</CardTitle>
                      <CardDescription>
                        Dutch Energy street-level consumption context for this meter.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <SpatialContextSection
                        spatialContext={spatial_context}
                        baselineAnnualKwh={customer.baseline_annual_kwh}
                        peerComparison={peer_comparison}
                        showHeading={false}
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Loss estimate</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      <Row label="Estimated loss" value={formatEnergyKwh(risk.estimated_loss_kwh)} />
                      <Row
                        label="Estimated value"
                        value={formatCurrency(risk.estimated_loss_value, currency)}
                      />
                      <Row
                        label="Share of transformer loss"
                        value={formatPercent(loss_attribution_share)}
                      />
                      <Row
                        label="Inspection priority"
                        value={formatNumber(Math.round(risk.inspection_priority))}
                      />
                      <Row label="Model version" value={risk.model_version} />
                      <Row label="Feature version" value={risk.feature_version} />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Risk components</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {(Object.keys(COMPONENT_LABELS) as (keyof RiskComponents)[]).map((key) => (
                        <div key={key} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{COMPONENT_LABELS[key]}</span>
                            <span className="tabular-nums">
                              {Math.round(risk.components[key] * 100)}%
                            </span>
                          </div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full bg-primary"
                              style={{ width: `${Math.round(risk.components[key] * 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  <Card className="border-info/30 bg-info/5">
                    <CardContent className="flex gap-2 p-4 text-sm">
                      <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" />
                      <ul className="space-y-1.5 text-muted-foreground">
                        {notes.map((note, i) => (
                          <li key={i}>{note}</li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </>
          );
        }}
      </QueryBoundary>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
