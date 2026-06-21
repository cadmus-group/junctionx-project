import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { GeoJsonLayer, PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import type { Color, Layer, PickingInfo } from "@deck.gl/core";
import type {
  Feature,
  FeatureCollection,
  LineString,
  Point,
  Position,
  RiskTier,
} from "@gridtrace/contracts";
import {
  NEUTRAL_OUTLINE_RGBA,
  riskScoreRgba,
  riskTierRgba,
  ROUTE_RGBA,
  SELECTED_RGBA,
  TRANSFORMER_RGBA,
  type RGBAColor,
} from "../style";

export interface RiskPointProperties {
  entity_id: string;
  entity_type?: string;
  name?: string;
  external_ref?: string;
  risk_score?: number | null;
  risk_tier?: RiskTier | null;
  estimated_loss_kwh?: number | null;
  [key: string]: unknown;
}

export type RiskPointFeature = Feature<Point, RiskPointProperties>;
export type RiskPointCollection = FeatureCollection<Point, RiskPointProperties>;

export interface LayerCallbacks {
  onSelect?: (id: string, feature: RiskPointFeature) => void;
  onHover?: (id: string | null, feature: RiskPointFeature | null, x: number, y: number) => void;
  selectedId?: string | null;
}

function pointPosition(f: RiskPointFeature): Position {
  return f.geometry.coordinates;
}

function pickHandler(
  cb: ((id: string, feature: RiskPointFeature) => void) | undefined
) {
  return (info: PickingInfo) => {
    const object = info.object as RiskPointFeature | undefined;
    if (object && cb) cb(object.properties.entity_id, object);
  };
}

export interface CustomerRiskLayerOptions extends LayerCallbacks {
  id?: string;
  visible?: boolean;
  radiusScale?: number;
}

export function createCustomerRiskLayer(
  data: RiskPointCollection,
  options: CustomerRiskLayerOptions = {}
): Layer {
  const { id = "customer-risk", visible = true, radiusScale = 1, selectedId, onSelect, onHover } =
    options;
  return new ScatterplotLayer<RiskPointFeature>({
    id,
    data: data.features,
    visible,
    pickable: true,
    stroked: true,
    filled: true,
    radiusUnits: "pixels",
    radiusMinPixels: 3,
    radiusMaxPixels: 22,
    lineWidthMinPixels: 1,
    getPosition: pointPosition,
    getRadius: (f) => {
      const score = f.properties.risk_score ?? 0;
      return (4 + (score / 100) * 10) * radiusScale;
    },
    getFillColor: (f) => riskScoreRgba(f.properties.risk_score),
    getLineColor: (f): RGBAColor =>
      f.properties.entity_id === selectedId ? SELECTED_RGBA : NEUTRAL_OUTLINE_RGBA,
    getLineWidth: (f) => (f.properties.entity_id === selectedId ? 3 : 1),
    onClick: pickHandler(onSelect),
    onHover: (info: PickingInfo) => {
      const object = info.object as RiskPointFeature | undefined;
      onHover?.(object?.properties.entity_id ?? null, object ?? null, info.x, info.y);
    },
    updateTriggers: {
      getLineColor: [selectedId],
      getLineWidth: [selectedId],
    },
  });
}

export interface TransformerLayerOptions extends LayerCallbacks {
  id?: string;
  visible?: boolean;
}

export function createTransformerLayer(
  data: RiskPointCollection,
  options: TransformerLayerOptions = {}
): Layer {
  const { id = "transformers", visible = true, selectedId, onSelect, onHover } = options;
  return new ScatterplotLayer<RiskPointFeature>({
    id,
    data: data.features,
    visible,
    pickable: true,
    stroked: true,
    filled: true,
    radiusUnits: "pixels",
    radiusMinPixels: 7,
    radiusMaxPixels: 16,
    lineWidthMinPixels: 2,
    getPosition: pointPosition,
    getRadius: 10,
    getFillColor: (f): RGBAColor =>
      f.properties.risk_tier ? riskTierRgba(f.properties.risk_tier) : TRANSFORMER_RGBA,
    getLineColor: (f): RGBAColor =>
      f.properties.entity_id === selectedId ? SELECTED_RGBA : NEUTRAL_OUTLINE_RGBA,
    getLineWidth: (f) => (f.properties.entity_id === selectedId ? 4 : 2),
    onClick: pickHandler(onSelect),
    onHover: (info: PickingInfo) => {
      const object = info.object as RiskPointFeature | undefined;
      onHover?.(object?.properties.entity_id ?? null, object ?? null, info.x, info.y);
    },
    updateTriggers: {
      getLineColor: [selectedId],
      getLineWidth: [selectedId],
    },
  });
}

export interface H3RiskLayerOptions {
  id?: string;
  visible?: boolean;
  opacity?: number;
  riskAccessor?: (properties: Record<string, unknown>) => number;
}

/**
 * Hotspot risk surface. The GIS hotspots endpoint returns polygon features
 * (H3 cell geometries already resolved server-side); this renders them as a
 * graduated risk fill via a GeoJsonLayer.
 */
export function createH3RiskLayer(
  data: FeatureCollection,
  options: H3RiskLayerOptions = {}
): Layer {
  const {
    id = "hotspots",
    visible = true,
    opacity = 0.45,
    riskAccessor = (p) => Number(p.risk_score ?? p.mean_risk ?? 0),
  } = options;
  return new GeoJsonLayer({
    id,
    data,
    visible,
    opacity,
    pickable: true,
    filled: true,
    stroked: true,
    getFillColor: (f: { properties?: Record<string, unknown> | null }) =>
      riskScoreRgba(riskAccessor(f.properties ?? {}), 150),
    getLineColor: [128, 128, 124, 70],
    getLineWidth: 1,
    lineWidthMinPixels: 1,
  });
}

/**
 * Diverging blue → red color ramp mirroring the MapLibre "Create a heatmap
 * layer" example. Ordered low → high density for deck.gl's `colorRange`.
 */
export const HEATMAP_COLOR_RANGE: Color[] = [
  [33, 102, 172],
  [103, 169, 207],
  [209, 229, 240],
  [253, 219, 199],
  [239, 138, 98],
  [178, 24, 43],
];

export interface RiskHeatmapLayerOptions {
  id?: string;
  visible?: boolean;
  /** Multiplier on aggregated weight; higher = hotter. */
  intensity?: number;
  /** Distribution radius in pixels for each point. */
  radiusPixels?: number;
  /** Fraction of max weight below which pixels fade out (blur-like edge). */
  threshold?: number;
  opacity?: number;
  /** Maps a feature's risk score to a heat weight. Defaults to risk_score/100. */
  weightAccessor?: (feature: RiskPointFeature) => number;
}

/**
 * Risk density heatmap over metering-point / anomaly features. Weights each
 * point by its risk score so concentrations of high-risk points read as the
 * hottest areas — the analytical analogue of the MapLibre heatmap example.
 */
export function createRiskHeatmapLayer(
  data: RiskPointCollection,
  options: RiskHeatmapLayerOptions = {}
): Layer {
  const {
    id = "risk-heatmap",
    visible = true,
    intensity = 2,
    radiusPixels = 48,
    threshold = 0.03,
    opacity = 0.8,
    weightAccessor = (f) => {
      const score = f.properties.risk_score;
      return score == null ? 0.2 : Math.max(0.05, score / 100);
    },
  } = options;
  return new HeatmapLayer<RiskPointFeature>({
    id,
    data: data.features,
    visible,
    opacity,
    pickable: false,
    radiusPixels,
    intensity,
    threshold,
    colorRange: HEATMAP_COLOR_RANGE,
    getPosition: pointPosition,
    getWeight: weightAccessor,
  });
}

export interface InspectionRouteLayerOptions {
  id?: string;
  visible?: boolean;
  color?: RGBAColor;
}

export function createInspectionRouteLayer(
  route: LineString,
  options: InspectionRouteLayerOptions = {}
): Layer {
  const { id = "inspection-route", visible = true, color = ROUTE_RGBA } = options;
  return new PathLayer<{ path: Position[] }>({
    id,
    data: [{ path: route.coordinates }],
    visible,
    widthUnits: "pixels",
    getPath: (d) => d.path,
    getColor: color,
    getWidth: 4,
    widthMinPixels: 3,
    capRounded: true,
    jointRounded: true,
  });
}
