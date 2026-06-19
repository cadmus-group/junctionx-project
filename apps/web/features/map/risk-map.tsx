"use client";

import type { FeatureCollection, Point } from "@gridtrace/contracts";
import {
  createCustomerRiskLayer,
  createH3RiskLayer,
  createTransformerLayer,
  fitBoundsToGeometry,
  GridTraceMap,
  MapLegend,
  type RiskPointCollection,
  type RiskPointFeature,
} from "@gridtrace/maps";
import { Card, DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuTrigger, Button, Label, Slider } from "@gridtrace/ui";
import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";
import { useMemo, useState } from "react";
import { useApi } from "@/lib/client";
import { getPublicEnv } from "@/lib/env";
import { useGlobalFilters } from "@/lib/use-filters";
import { FilterBar } from "@/components/filter-bar";
import { EntityDrawer } from "./entity-drawer";

const EMPTY: RiskPointCollection = { type: "FeatureCollection", features: [] };

export function RiskMap() {
  const api = useApi();
  const { filters, setFilters } = useGlobalFilters();
  const { NEXT_PUBLIC_MAP_STYLE_URL } = getPublicEnv();

  const [threshold, setThreshold] = useState<number>(filters.minRisk ?? 50);
  const [visible, setVisible] = useState({ customers: true, transformers: true, hotspots: true });

  const anomaliesQuery = useQuery(api.gis.anomalies({ min_risk: threshold }));
  const hotspotsQuery = useQuery(api.gis.hotspots({ min_risk: 0 }));
  const assetsQuery = useQuery(api.assets.list({ page: 1, page_size: 50, asset_type: "transformer" }));

  const customers = (anomaliesQuery.data as RiskPointCollection | undefined) ?? EMPTY;
  const hotspots = (hotspotsQuery.data as FeatureCollection | undefined) ?? {
    type: "FeatureCollection",
    features: [],
  };

  const transformers = useMemo<RiskPointCollection>(() => {
    const items = assetsQuery.data?.items ?? [];
    return {
      type: "FeatureCollection",
      features: items
        .filter((a) => a.geometry)
        .map((a) => ({
          type: "Feature" as const,
          id: a.id,
          geometry: a.geometry as Point,
          properties: {
            entity_id: a.id,
            entity_type: "transformer",
            name: a.name,
            external_ref: a.external_id,
            risk_score: a.risk_score,
            risk_tier: a.risk_tier,
          },
        })),
    };
  }, [assetsQuery.data]);

  const selectedId = filters.selected ?? null;

  const select = (id: string) => setFilters({ selected: id }, { replace: true });

  const layers = useMemo(() => {
    const result = [];
    if (visible.hotspots) {
      result.push(createH3RiskLayer(hotspots, { id: "hotspots" }));
    }
    if (visible.transformers) {
      result.push(
        createTransformerLayer(transformers, {
          selectedId,
          onSelect: (id: string) => select(id),
        })
      );
    }
    if (visible.customers) {
      result.push(
        createCustomerRiskLayer(customers, {
          selectedId,
          onSelect: (id: string) => select(id),
        })
      );
    }
    return result;
    // select is stable enough for the demo; deps cover the data + view state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customers, transformers, hotspots, visible, selectedId]);

  const bounds = useMemo(() => fitBoundsToGeometry(customers as FeatureCollection), [customers]);

  const onThreshold = (value: number) => {
    setThreshold(value);
    setFilters({ minRisk: value }, { replace: true });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border px-6 py-4">
        <FilterBar showTier={false} />
        <div className="flex items-end gap-4">
          <div className="w-48 space-y-1">
            <Label className="text-xs text-muted-foreground">
              Risk threshold: {threshold}
            </Label>
            <Slider value={threshold} min={0} max={100} step={1} onValueChange={onThreshold} />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Layers className="h-4 w-4" />
                Layers
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuCheckboxItem
                checked={visible.hotspots}
                onCheckedChange={(c) => setVisible((v) => ({ ...v, hotspots: !!c }))}
              >
                Hotspots
              </DropdownMenuCheckboxItem>
              <DropdownMenuCheckboxItem
                checked={visible.transformers}
                onCheckedChange={(c) => setVisible((v) => ({ ...v, transformers: !!c }))}
              >
                Transformers
              </DropdownMenuCheckboxItem>
              <DropdownMenuCheckboxItem
                checked={visible.customers}
                onCheckedChange={(c) => setVisible((v) => ({ ...v, customers: !!c }))}
              >
                Customer risk
              </DropdownMenuCheckboxItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="relative flex-1">
        <Card className="absolute inset-3 z-0 overflow-hidden p-0">
          <GridTraceMap
            styleUrl={NEXT_PUBLIC_MAP_STYLE_URL}
            layers={layers}
            fitBounds={bounds}
            className="relative h-full w-full"
          >
            <MapLegend />
          </GridTraceMap>
        </Card>
      </div>

      <EntityDrawer
        selectedId={selectedId}
        onClose={() => setFilters({ selected: undefined }, { replace: true })}
      />
    </div>
  );
}

export type { RiskPointFeature };
