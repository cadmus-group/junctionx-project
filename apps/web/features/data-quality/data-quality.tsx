"use client";

import { formatDateTime } from "@gridtrace/domain";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert } from "lucide-react";
import { useApi } from "@/lib/client";
import { PageHeader } from "@/components/page-header";
import { QueryBoundary } from "@/components/query-boundary";

interface SourceFreshness {
  source: string;
  cadence: string;
  lastSync: string;
  status: "ok" | "degraded";
}

interface MeterQualityRow {
  segment: string;
  coverage: number;
  estimatedReads: number;
  missingReads: number;
}

const SOURCES: SourceFreshness[] = [
  { source: "AMI meter readings", cadence: "Hourly", lastSync: "2025-06-30T05:00:00Z", status: "ok" },
  { source: "SCADA transformer telemetry", cadence: "15 min", lastSync: "2025-06-30T05:10:00Z", status: "ok" },
  { source: "Billing / CIS", cadence: "Daily", lastSync: "2025-06-29T22:00:00Z", status: "ok" },
  { source: "GIS network topology", cadence: "Weekly", lastSync: "2025-06-24T03:00:00Z", status: "degraded" },
];

const METER_QUALITY: MeterQualityRow[] = [
  { segment: "Jordaan", coverage: 0.98, estimatedReads: 1.2, missingReads: 0.3 },
  { segment: "De Pijp", coverage: 0.97, estimatedReads: 1.8, missingReads: 0.6 },
  { segment: "Amsterdam Oost", coverage: 0.95, estimatedReads: 2.4, missingReads: 1.1 },
  { segment: "Amsterdam Noord", coverage: 0.93, estimatedReads: 3.1, missingReads: 1.9 },
  { segment: "Zuidoost", coverage: 0.9, estimatedReads: 4.2, missingReads: 2.7 },
];

export function DataQuality() {
  const api = useApi();
  const healthQuery = useQuery(api.health);

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Data Quality"
        description="Source freshness and metering coverage feeding the risk pipeline."
      />
      <div className="space-y-4 p-6">
        <QueryBoundary query={healthQuery}>
          {(health) => (
            <Card>
              <CardHeader>
                <CardTitle>Pipeline health</CardTitle>
                <CardDescription>
                  API status {health.status} · database {health.database} · checked{" "}
                  {formatDateTime(health.time)}
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </QueryBoundary>

        <Card>
          <CardHeader>
            <CardTitle>Source freshness</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Cadence</TableHead>
                  <TableHead>Last sync</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {SOURCES.map((s) => (
                  <TableRow key={s.source}>
                    <TableCell className="font-medium">{s.source}</TableCell>
                    <TableCell>{s.cadence}</TableCell>
                    <TableCell>{formatDateTime(s.lastSync)}</TableCell>
                    <TableCell>
                      {s.status === "ok" ? (
                        <Badge variant="success">
                          <CheckCircle2 className="h-3 w-3" /> Fresh
                        </Badge>
                      ) : (
                        <Badge variant="warning">
                          <CircleAlert className="h-3 w-3" /> Stale
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Meter data quality</CardTitle>
            <CardDescription>
              Estimated vs missing reads by region. Low coverage weakens risk confidence.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Region</TableHead>
                  <TableHead>Coverage</TableHead>
                  <TableHead>Estimated reads</TableHead>
                  <TableHead>Missing reads</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {METER_QUALITY.map((r) => (
                  <TableRow key={r.segment}>
                    <TableCell className="font-medium">{r.segment}</TableCell>
                    <TableCell className="tabular-nums">{Math.round(r.coverage * 100)}%</TableCell>
                    <TableCell className="tabular-nums">{r.estimatedReads}%</TableCell>
                    <TableCell className="tabular-nums">{r.missingReads}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
