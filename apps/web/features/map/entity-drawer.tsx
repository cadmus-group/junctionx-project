"use client";

import type { Currency } from "@gridtrace/config";
import { formatCurrency, formatEnergyKwh } from "@gridtrace/domain";
import {
  Button,
  RiskBadge,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Skeleton,
} from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { useApi } from "@/lib/client";
import { SpatialContextSection } from "@/src/components/customers/customer-drawer";

export function EntityDrawer({
  selectedId,
  selectedType,
  onClose,
}: {
  selectedId: string | null;
  selectedType?: "customer" | "transformer" | null;
  onClose: () => void;
}) {
  const isTransformer = selectedType === "transformer";
  return (
    <Sheet open={!!selectedId} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <SheetContent side="right" className="w-[24rem]">
        {selectedId ? (
          isTransformer ? (
            <TransformerPanel id={selectedId} />
          ) : (
            <CustomerPanel id={selectedId} />
          )
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function CustomerPanel({ id }: { id: string }) {
  const api = useApi();
  const query = useQuery(api.customers.riskProfile(id));

  if (query.isPending) return <Skeleton className="h-40 w-full" />;
  if (query.isError || !query.data)
    return <p className="text-sm text-danger">Could not load customer.</p>;

  const { customer, risk, peer_comparison, spatial_context } = query.data;
  const currency = risk.currency as Currency;
  return (
    <>
      <SheetHeader>
        <div className="flex items-center justify-between gap-2">
          <SheetTitle>{customer.external_ref}</SheetTitle>
          <RiskBadge tier={risk.risk_tier} score={risk.risk_score} />
        </div>
        <SheetDescription>
          {customer.customer_type} · {customer.region_id ?? "—"}
        </SheetDescription>
      </SheetHeader>
      <dl className="mt-4 space-y-3 text-sm">
        <Row label="Estimated loss" value={formatEnergyKwh(risk.estimated_loss_kwh)} />
        <Row
          label="Estimated value"
          value={formatCurrency(risk.estimated_loss_value, currency)}
        />
        <Row label="Confidence" value={`${Math.round(risk.confidence * 100)}%`} />
        <Row label="Model" value={risk.model_version} />
      </dl>
      <SpatialContextSection
        spatialContext={spatial_context}
        baselineAnnualKwh={customer.baseline_annual_kwh}
        peerComparison={peer_comparison}
      />
      <Button asChild variant="outline" size="sm" className="mt-4">
        <Link href={`/customers/${customer.id}`}>
          Open investigation
          <ExternalLink className="h-3.5 w-3.5" />
        </Link>
      </Button>
    </>
  );
}

function TransformerPanel({ id }: { id: string }) {
  const api = useApi();
  const query = useQuery(api.assets.reconciliation(id));

  if (query.isPending) return <Skeleton className="h-40 w-full" />;
  if (query.isError || !query.data)
    return <p className="text-sm text-danger">Could not load transformer.</p>;

  const recon = query.data;
  const currency = recon.currency as Currency;
  return (
    <>
      <SheetHeader>
        <div className="flex items-center justify-between gap-2">
          <SheetTitle>{recon.name}</SheetTitle>
          <RiskBadge tier={recon.risk_tier} score={recon.risk_score} />
        </div>
        <SheetDescription>Transformer digital twin</SheetDescription>
      </SheetHeader>
      <dl className="mt-4 space-y-3 text-sm">
        <Row label="Energy input" value={formatEnergyKwh(recon.energy_input_kwh)} />
        <Row label="Metered output" value={formatEnergyKwh(recon.metered_output_kwh)} />
        <Row label="Unexplained loss" value={formatEnergyKwh(recon.unexplained_loss_kwh)} />
        <Row
          label="Unexplained ratio"
          value={`${(recon.unexplained_loss_ratio * 100).toFixed(2)}%`}
        />
        <Row label="Estimated value" value={formatCurrency(recon.estimated_loss_value, currency)} />
      </dl>
      <Button asChild variant="outline" size="sm" className="mt-4">
        <Link href={`/assets/transformers/${recon.transformer_id}`}>
          Open digital twin
          <ExternalLink className="h-3.5 w-3.5" />
        </Link>
      </Button>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}
