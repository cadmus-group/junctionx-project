import type {
  Customer,
  EntityType,
  GridAsset,
  InspectionCase,
  InspectionQueueItem,
  Point,
  RiskComponents,
  RiskExplanation,
  RiskScore,
  RiskTier,
} from "@gridtrace/contracts";
import { riskTierForScore } from "@gridtrace/domain";
import { isoFromDayOffset, makeRng, pad, round } from "./seed";

export const DEMO_OPERATOR_ID = "op-nl-001";
export const DEMO_CURRENCY = "EUR";
export const MODEL_VERSION = "risk-gbm-2025.06.1";
export const FEATURE_VERSION = "features-2025.06.0";

export const CUSTOMER_TYPES = ["residential", "commercial", "industrial"] as const;
export const TARIFF_TYPES = ["single", "double", "dynamic"] as const;
export const BUILDING_TYPES = ["apartment", "detached", "row_house", "office", "warehouse"] as const;

function point(lon: number, lat: number): Point {
  return { type: "Point", coordinates: [round(lon, 6), round(lat, 6)] };
}

export interface CustomerFactoryOptions {
  id?: string;
  index?: number;
  operatorId?: string;
  transformerId?: string | null;
  feederId?: string | null;
  regionId?: string | null;
  riskScore?: number | null;
  geometry?: Point | null;
  seed?: number;
  overrides?: Partial<Customer>;
}

export function customerFactory(options: CustomerFactoryOptions = {}): Customer {
  const index = options.index ?? 1;
  const rng = makeRng((options.seed ?? 7000) + index);
  const id = options.id ?? `cust-${pad(index, 4)}`;
  const score = options.riskScore ?? round(rng() * 100, 1);
  const customerType = CUSTOMER_TYPES[Math.floor(rng() * CUSTOMER_TYPES.length)]!;
  const geometry =
    options.geometry ??
    point(4.86 + rng() * 0.12, 52.33 + rng() * 0.09);
  return {
    id,
    operator_id: options.operatorId ?? DEMO_OPERATOR_ID,
    external_ref: `NL-MTR-${pad(index, 5)}`,
    transformer_id: options.transformerId ?? null,
    feeder_id: options.feederId ?? null,
    region_id: options.regionId ?? null,
    customer_type: customerType,
    tariff_type: TARIFF_TYPES[Math.floor(rng() * TARIFF_TYPES.length)]!,
    building_type: BUILDING_TYPES[Math.floor(rng() * BUILDING_TYPES.length)]!,
    geometry,
    risk_score: options.riskScore === null ? null : score,
    risk_tier: options.riskScore === null ? null : riskTierForScore(score),
    ...options.overrides,
  };
}

export interface TransformerFactoryOptions {
  id?: string;
  index?: number;
  operatorId?: string;
  regionId?: string | null;
  riskScore?: number | null;
  geometry?: Point | null;
  capacityKva?: number;
  seed?: number;
  overrides?: Partial<GridAsset>;
}

export function transformerFactory(options: TransformerFactoryOptions = {}): GridAsset {
  const index = options.index ?? 1;
  const rng = makeRng((options.seed ?? 3000) + index);
  const id = options.id ?? `tx-${pad(index, 3)}`;
  const score = options.riskScore ?? round(rng() * 100, 1);
  const geometry = options.geometry ?? point(4.87 + rng() * 0.1, 52.34 + rng() * 0.07);
  return {
    id,
    operator_id: options.operatorId ?? DEMO_OPERATOR_ID,
    parent_asset_id: null,
    asset_type: "transformer",
    external_id: `NL-TX-${pad(index, 4)}`,
    name: `Transformer ${pad(index, 3)}`,
    voltage_level: "10kV/400V",
    capacity_kva: options.capacityKva ?? 250 + Math.floor(rng() * 16) * 50,
    geometry,
    region_id: options.regionId ?? null,
    risk_tier: options.riskScore === null ? null : riskTierForScore(score),
    risk_score: options.riskScore === null ? null : score,
    ...options.overrides,
  };
}

export interface RiskScoreFactoryOptions {
  entityId: string;
  entityType?: EntityType;
  score: number;
  confidence?: number;
  estimatedLossKwh?: number;
  estimatedLossValue?: number;
  currency?: string;
  components?: Partial<RiskComponents>;
  explanations?: RiskExplanation[];
  inspectionPriority?: number;
  scoredAtDayOffset?: number;
  seed?: number;
  overrides?: Partial<RiskScore>;
}

function defaultExplanations(tier: RiskTier): RiskExplanation[] {
  const base: RiskExplanation[] = [
    {
      feature: "night_consumption_ratio",
      label: "Elevated overnight consumption vs peers",
      contribution: 0.31,
      direction: "increases",
      detail: "Overnight usage is well above the neighborhood median.",
    },
    {
      feature: "transformer_imbalance",
      label: "Parent transformer shows unexplained loss",
      contribution: 0.27,
      direction: "increases",
      detail: "Feeds from a transformer with a high unexplained-loss ratio.",
    },
    {
      feature: "meter_event_count",
      label: "Recent meter tamper/health events",
      contribution: 0.18,
      direction: "increases",
    },
    {
      feature: "billing_continuity",
      label: "Consistent billing history",
      contribution: 0.12,
      direction: "decreases",
      detail: "Long, stable billing record reduces estimated risk.",
    },
  ];
  return tier === "LOW" || tier === "WATCH"
    ? base.map((e) => ({ ...e, contribution: e.contribution * 0.4 }))
    : base;
}

export function riskScoreFactory(options: RiskScoreFactoryOptions): RiskScore {
  const rng = makeRng((options.seed ?? 9000) + Math.round(options.score));
  const tier = riskTierForScore(options.score);
  const norm = options.score / 100;
  const components: RiskComponents = {
    supervised_probability: round(Math.min(0.99, norm * 0.95 + rng() * 0.05), 3),
    anomaly_score: round(Math.min(1, norm * 0.9 + rng() * 0.1), 3),
    grid_imbalance_score: round(Math.min(1, norm * 0.85 + rng() * 0.12), 3),
    peer_score: round(Math.min(1, norm * 0.8 + rng() * 0.15), 3),
    spatial_score: round(Math.min(1, norm * 0.7 + rng() * 0.2), 3),
    ...options.components,
  };
  return {
    id: `risk-${options.entityId}`,
    entity_type: options.entityType ?? "customer",
    entity_id: options.entityId,
    scored_at: isoFromDayOffset(options.scoredAtDayOffset ?? 180),
    risk_score: round(options.score, 1),
    risk_tier: tier,
    components,
    confidence: options.confidence ?? round(0.55 + norm * 0.4, 2),
    estimated_loss_kwh: options.estimatedLossKwh ?? round(norm * 4200, 0),
    estimated_loss_value: options.estimatedLossValue ?? round(norm * 4200 * 0.28, 0),
    currency: options.currency ?? DEMO_CURRENCY,
    inspection_priority: options.inspectionPriority ?? round(options.score, 0),
    explanations: options.explanations ?? defaultExplanations(tier),
    model_version: MODEL_VERSION,
    feature_version: FEATURE_VERSION,
    ...options.overrides,
  };
}

export interface InspectionQueueFactoryOptions {
  customerId: string;
  externalRef?: string;
  score: number;
  estimatedLossKwh?: number;
  estimatedLossValue?: number;
  recommendedAction?: string;
  regionName?: string | null;
  currency?: string;
  overrides?: Partial<InspectionQueueItem>;
}

export function inspectionQueueItemFactory(
  options: InspectionQueueFactoryOptions
): InspectionQueueItem {
  const norm = options.score / 100;
  return {
    customer_id: options.customerId,
    external_ref: options.externalRef ?? `NL-MTR-${options.customerId}`,
    risk_score: round(options.score, 1),
    risk_tier: riskTierForScore(options.score),
    inspection_priority: round(options.score, 0),
    estimated_loss_kwh: options.estimatedLossKwh ?? round(norm * 4200, 0),
    estimated_loss_value: options.estimatedLossValue ?? round(norm * 4200 * 0.28, 0),
    currency: options.currency ?? DEMO_CURRENCY,
    recommended_action:
      options.recommendedAction ?? "On-site inspection: verify meter integrity and connections",
    region_name: options.regionName ?? null,
    ...options.overrides,
  };
}

export interface InspectionCaseFactoryOptions {
  id?: string;
  missionId: string;
  customerId: string;
  index?: number;
  riskScoreId?: string | null;
  status?: InspectionCase["status"];
  recommendedAction?: string | null;
  notes?: string | null;
  overrides?: Partial<InspectionCase>;
}

export function inspectionFactory(options: InspectionCaseFactoryOptions): InspectionCase {
  const index = options.index ?? 1;
  return {
    id: options.id ?? `case-${pad(index, 4)}`,
    mission_id: options.missionId,
    customer_id: options.customerId,
    risk_score_id: options.riskScoreId ?? `risk-${options.customerId}`,
    status: options.status ?? "queued",
    priority_rank: index,
    scheduled_at: null,
    assigned_to: null,
    recommended_action: options.recommendedAction ?? "Verify meter integrity on-site",
    notes: options.notes ?? null,
    ...options.overrides,
  };
}
