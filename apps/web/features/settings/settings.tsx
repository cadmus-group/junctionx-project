"use client";

import { SUPPORTED_CURRENCIES, SUPPORTED_LOCALES } from "@gridtrace/config";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gridtrace/ui";
import { useApi } from "@/lib/client";
import { useQuery } from "@tanstack/react-query";
import { getPublicEnv } from "@/lib/env";
import { PageHeader } from "@/components/page-header";

export function Settings() {
  const api = useApi();
  const env = getPublicEnv();
  const healthQuery = useQuery(api.health);

  return (
    <div className="flex flex-col">
      <PageHeader title="Settings" description="Environment, locale, and demo configuration." />
      <div className="grid grid-cols-1 gap-4 p-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Environment</CardTitle>
            <CardDescription>Public runtime configuration.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="API base URL" value={env.NEXT_PUBLIC_API_BASE_URL} />
            <Row label="Map style" value={env.NEXT_PUBLIC_MAP_STYLE_URL} />
            <Row label="Demo mode" value={env.NEXT_PUBLIC_DEMO_MODE ? "Enabled" : "Disabled"} />
            <Row
              label="Backend health"
              value={healthQuery.data ? healthQuery.data.status : "checking…"}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Regional</CardTitle>
            <CardDescription>Operator locale and currency support.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Locales" value={SUPPORTED_LOCALES.join(", ")} />
            <Row label="Currencies" value={SUPPORTED_CURRENCIES.join(", ")} />
            <Row label="Default operator" value="Randstad Net Beheer (NL)" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  );
}
