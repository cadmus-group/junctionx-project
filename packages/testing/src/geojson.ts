import type { Feature, FeatureCollection, Point, Polygon } from "@gridtrace/contracts";
import { getDemoDataset, type DemoDataset } from "./data";
import { round } from "./seed";

type RiskPointProps = {
  entity_id: string;
  entity_type: string;
  name?: string;
  external_ref?: string;
  risk_score: number | null;
  risk_tier: string | null;
  estimated_loss_kwh?: number | null;
  baseline_annual_kwh?: number | null;
  street_smartmeter_perc?: number | null;
};

export function customersGeoJson(
  data: DemoDataset = getDemoDataset(),
  minRisk = 0
): FeatureCollection<Point, RiskPointProps> {
  const features: Feature<Point, RiskPointProps>[] = data.customers
    .filter((c) => c.geometry && (c.risk_score ?? 0) >= minRisk)
    .map((c) => ({
      type: "Feature",
      id: c.id,
      geometry: c.geometry as Point,
      properties: {
        entity_id: c.id,
        entity_type: "customer",
        external_ref: c.external_ref,
        risk_score: c.risk_score,
        risk_tier: c.risk_tier,
        estimated_loss_kwh: data.riskScores.get(c.id)?.estimated_loss_kwh ?? null,
        baseline_annual_kwh: c.baseline_annual_kwh,
        street_smartmeter_perc: c.street_smartmeter_perc,
      },
    }));
  return { type: "FeatureCollection", features };
}

export function transformersGeoJson(
  data: DemoDataset = getDemoDataset()
): FeatureCollection<Point, RiskPointProps> {
  const features: Feature<Point, RiskPointProps>[] = data.transformers
    .filter((t) => t.geometry)
    .map((t) => ({
      type: "Feature",
      id: t.id,
      geometry: t.geometry as Point,
      properties: {
        entity_id: t.id,
        entity_type: "transformer",
        name: t.name,
        external_ref: t.external_id,
        risk_score: t.risk_score,
        risk_tier: t.risk_tier,
        estimated_loss_kwh: data.reconciliations.get(t.id)?.unexplained_loss_kwh ?? null,
      },
    }));
  return { type: "FeatureCollection", features };
}

function hexCell(center: [number, number], radius: number): Polygon {
  const coords: [number, number][] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i + Math.PI / 6;
    coords.push([
      round(center[0] + radius * Math.cos(angle) * 1.6, 6),
      round(center[1] + radius * Math.sin(angle), 6),
    ]);
  }
  coords.push(coords[0]!);
  return { type: "Polygon", coordinates: [coords] };
}

/** Aggregate customer risk into hex hotspot polygons (resolved server-side in prod). */
export function hotspotsGeoJson(
  data: DemoDataset = getDemoDataset(),
  minRisk = 0
): FeatureCollection<Polygon, { h3_index: string; risk_score: number; customer_count: number }> {
  const features = data.regions.map((region, idx) => {
    const regionCustomers = data.customers.filter((c) => c.region_id === region.id);
    const meanRisk =
      regionCustomers.reduce((sum, c) => sum + (c.risk_score ?? 0), 0) /
      Math.max(1, regionCustomers.length);
    return {
      type: "Feature" as const,
      id: region.id,
      geometry: hexCell(region.center, 0.012),
      properties: {
        h3_index: `8a19${idx}ffffff`,
        risk_score: round(meanRisk, 1),
        customer_count: regionCustomers.length,
      },
    };
  });
  return {
    type: "FeatureCollection",
    features: features.filter((f) => f.properties.risk_score >= minRisk),
  };
}
