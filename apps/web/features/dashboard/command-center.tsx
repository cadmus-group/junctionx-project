"use client";

import { LossTrendChart, RiskDistributionChart } from "@gridtrace/charts";
import type { Customer, DashboardSummary } from "@gridtrace/contracts";
import type { Currency } from "@gridtrace/config";
import { formatCurrency, formatEnergyKwh, formatNumber } from "@gridtrace/domain";
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
import { AlertTriangle, ClipboardList, Euro, Zap } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { useApi } from "@/lib/client";
import { useGlobalFilters } from "@/lib/use-filters";
import { CardSkeletonGrid } from "@/components/loading";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";
import { FilterBar } from "@/components/filter-bar";

export function CommandCenter() {
  const api = useApi();
  const { filters } = useGlobalFilters();
  const params = { from: filters.from, to: filters.to, regionId: filters.regionId };

  const summaryQuery = useQuery(api.dashboard.summary(params));
  const trendQuery = useQuery(api.dashboard.lossTrend(params));
  const topRiskQuery = useQuery(api.customers.list({ min_risk: 70, page: 1, page_size: 6 }));

  // Most-recent period-over-period change in unexplained loss (real, from the trend).
  const lossDelta = useMemo(() => {
    const pts = trendQuery.data?.points;
    if (!pts || pts.length < 2) return undefined;
    const last = pts[pts.length - 1]?.unexplained_loss_kwh ?? 0;
    const prev = pts[pts.length - 2]?.unexplained_loss_kwh ?? 0;
    return prev > 0 ? (last - prev) / prev : undefined;
  }, [trendQuery.data]);

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Command Center"
        description="Operator-wide view of unexplained losses, risk exposure, and inspection load."
      />
      <div className="space-y-4 p-6">
        <FilterBar showTier={false} />

        <QueryBoundary query={summaryQuery} loading={<CardSkeletonGrid />}>
          {(summary) => <KpiRow summary={summary} lossDelta={lossDelta} />}
        </QueryBoundary>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Loss trend</CardTitle>
              <CardDescription>
                Energy input vs metered output, technical and unexplained losses (kWh).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <QueryBoundary query={trendQuery}>
                {(trend) => <LossTrendChart trend={trend} height={300} />}
              </QueryBoundary>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Risk tier breakdown</CardTitle>
              <CardDescription>Scored customers by risk tier.</CardDescription>
            </CardHeader>
            <CardContent>
              <QueryBoundary query={summaryQuery}>
                {(summary) => (
                  <RiskDistributionChart breakdown={summary.risk_tier_breakdown} height={300} />
                )}
              </QueryBoundary>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Top risk customers</CardTitle>
            <CardDescription>
              Model-prioritized for inspection. Risk indicators require human confirmation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <QueryBoundary
              query={topRiskQuery}
              isEmpty={(page) => page.items.length === 0}
              emptyTitle="No high-risk customers in range"
            >
              {(page) => <TopRiskList customers={page.items} />}
            </QueryBoundary>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function KpiRow({ summary, lossDelta }: { summary: DashboardSummary; lossDelta?: number }) {
  const currency = summary.currency as Currency;
  const flagged = summary.high_risk_count + summary.critical_risk_count;
  const flaggedPct =
    summary.total_customers > 0 ? (flagged / summary.total_customers) * 100 : 0;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="Unexplained loss"
        value={formatEnergyKwh(summary.total_unexplained_loss_kwh)}
        icon={Zap}
        tone="negative"
        delta={lossDelta}
        deltaInvert
        hint={`${formatNumber(summary.total_transformers)} transformers`}
      />
      <KpiCard
        label="Estimated loss value"
        value={formatCurrency(summary.total_estimated_loss_value, currency)}
        icon={Euro}
        tone="negative"
        delta={lossDelta}
        deltaInvert
        hint="vs previous period"
      />
      <Link
        href="/inspections/flagged"
        className="block h-full rounded-[4px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <KpiCard
          label="Flagged for review"
          value={formatNumber(flagged)}
          icon={AlertTriangle}
          tone="warning"
          hint={`${summary.critical_risk_count} critical · ${flaggedPct.toFixed(1)}% of ${formatNumber(summary.total_customers)} scored`}
          className="h-full transition-colors hover:border-foreground/40"
        />
      </Link>
      <Link
        href="/inspections"
        className="block h-full rounded-[4px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <KpiCard
          label="Open inspections"
          value={formatNumber(summary.open_inspections)}
          icon={ClipboardList}
          tone="info"
          hint={`Model ${summary.model_version}`}
          className="h-full transition-colors hover:border-foreground/40"
        />
      </Link>
    </div>
  );
}

function TopRiskList({ customers }: { customers: Customer[] }) {
  return (
    <ul className="divide-y divide-border">
      {customers.map((c) => (
        <li key={c.id} className="flex items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <Link
              href={`/customers/${c.id}`}
              className="text-sm font-medium text-foreground hover:text-primary"
            >
              {c.external_ref}
            </Link>
            <p className="truncate text-xs text-muted-foreground">
              {c.customer_type} · {c.region_id ?? "—"}
            </p>
          </div>
          {c.risk_tier ? <RiskBadge tier={c.risk_tier} score={c.risk_score ?? undefined} /> : null}
        </li>
      ))}
    </ul>
  );
}
