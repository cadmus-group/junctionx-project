import type {
  Customer,
  CustomerReadings,
  DashboardSummary,
  GridAsset,
  InspectionCase,
  InspectionMission,
  InspectionOutcome,
  LossTrend,
  MeterReading,
  ModelRegistryEntry,
  PeerComparisonPoint,
  RiskScore,
  RiskTier,
  TransformerReconciliation,
} from "@gridtrace/contracts";
import { riskTierForScore } from "@gridtrace/domain";
import {
  customerFactory,
  DEMO_CURRENCY,
  DEMO_OPERATOR_ID,
  FEATURE_VERSION,
  inspectionFactory,
  MODEL_VERSION,
  riskScoreFactory,
  transformerFactory,
} from "./factories";
import { isoFromDayOffset, makeRng, pad, round } from "./seed";

export interface DemoRegion {
  id: string;
  name: string;
  center: [number, number];
}

export interface DemoOperator {
  id: string;
  name: string;
  country: string;
  currency: string;
}

const ENERGY_PRICE_PER_KWH = 0.28;
const CUSTOMER_COUNT = 200;
const TRANSFORMER_COUNT = 10;

export const DEMO_OPERATOR: DemoOperator = {
  id: DEMO_OPERATOR_ID,
  name: "Randstad Net Beheer",
  country: "Netherlands",
  currency: DEMO_CURRENCY,
};

export const DEMO_REGIONS: DemoRegion[] = [
  { id: "region-jordaan", name: "Jordaan", center: [4.8821, 52.3743] },
  { id: "region-de-pijp", name: "De Pijp", center: [4.8917, 52.3548] },
  { id: "region-oost", name: "Amsterdam Oost", center: [4.9295, 52.3601] },
  { id: "region-noord", name: "Amsterdam Noord", center: [4.9203, 52.3905] },
  { id: "region-zuidoost", name: "Zuidoost", center: [4.9609, 52.3148] },
];

const CRITICAL_TRANSFORMER_ID = "tx-001";
const CRITICAL_CUSTOMER_ID = "cust-0001";

export interface DemoDataset {
  operator: DemoOperator;
  regions: DemoRegion[];
  transformers: GridAsset[];
  customers: Customer[];
  riskScores: Map<string, RiskScore>;
  reconciliations: Map<string, TransformerReconciliation>;
  readings: Map<string, CustomerReadings>;
  peerComparison: Map<string, PeerComparisonPoint[]>;
  lossAttribution: Map<string, number>;
  models: ModelRegistryEntry[];
  missions: InspectionMission[];
  cases: InspectionCase[];
  outcomes: InspectionOutcome[];
}

function regionForIndex(index: number): DemoRegion {
  return DEMO_REGIONS[index % DEMO_REGIONS.length]!;
}

function buildReadings(customerId: string, baseDailyKwh: number, anomaly: boolean): CustomerReadings {
  const rng = makeRng(15000 + hashId(customerId));
  const readings: MeterReading[] = [];
  for (let day = 150; day <= 180; day++) {
    const seasonal = 1 + 0.15 * Math.sin((day / 7) * Math.PI);
    const noise = 0.9 + rng() * 0.2;
    const drift = anomaly && day > 165 ? 0.45 : 1;
    const consumption = round(baseDailyKwh * seasonal * noise * drift, 2);
    readings.push({
      timestamp: isoFromDayOffset(day),
      consumption_kwh: consumption,
      voltage: round(228 + rng() * 8, 1),
      current: round(consumption / 5, 2),
      power_factor: round(0.9 + rng() * 0.08, 3),
      reading_quality: anomaly && day > 165 && rng() > 0.6 ? "estimated" : "actual",
      source: "ami",
    });
  }
  return { customer_id: customerId, unit: "kWh", readings };
}

function buildPeerComparison(baseDailyKwh: number, anomaly: boolean): PeerComparisonPoint[] {
  const rng = makeRng(22000 + Math.round(baseDailyKwh));
  const points: PeerComparisonPoint[] = [];
  for (let i = 0; i < 14; i++) {
    const day = 167 + i;
    const peer = round(baseDailyKwh * (0.95 + rng() * 0.1), 2);
    const expected = round(peer * 1.02, 2);
    const customer = anomaly
      ? round(expected * (0.55 - i * 0.01), 2)
      : round(expected * (0.97 + rng() * 0.06), 2);
    points.push({
      timestamp: isoFromDayOffset(day),
      customer_kwh: customer,
      peer_median_kwh: peer,
      expected_kwh: expected,
    });
  }
  return points;
}

function hashId(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function buildReconciliation(transformer: GridAsset, index: number): TransformerReconciliation {
  if (transformer.id === CRITICAL_TRANSFORMER_ID) {
    const energyInput = 12400;
    const metered = 10550;
    const technical = 620;
    const unexplained = 1230;
    return {
      transformer_id: transformer.id,
      name: transformer.name,
      period_start: isoFromDayOffset(150),
      period_end: isoFromDayOffset(180),
      energy_input_kwh: energyInput,
      metered_output_kwh: metered,
      estimated_technical_loss_kwh: technical,
      unexplained_loss_kwh: unexplained,
      unexplained_loss_ratio: round(unexplained / energyInput, 4),
      customer_count: 42,
      risk_tier: "CRITICAL",
      risk_score: 88,
      waterfall: [
        { label: "Energy input", value: energyInput, kind: "input" },
        { label: "Metered output", value: metered, kind: "deduction" },
        { label: "Technical loss", value: technical, kind: "deduction" },
        { label: "Unexplained", value: unexplained, kind: "residual" },
      ],
      currency: DEMO_CURRENCY,
      estimated_loss_value: round(unexplained * ENERGY_PRICE_PER_KWH, 0),
    };
  }

  const rng = makeRng(31000 + index);
  const energyInput = round(8000 + rng() * 9000, 0);
  const ratio = round(0.02 + rng() * 0.05, 4);
  const unexplained = round(energyInput * ratio, 0);
  const technical = round(energyInput * (0.03 + rng() * 0.02), 0);
  const metered = round(energyInput - technical - unexplained, 0);
  const score = transformer.risk_score ?? round(rng() * 70, 1);
  return {
    transformer_id: transformer.id,
    name: transformer.name,
    period_start: isoFromDayOffset(150),
    period_end: isoFromDayOffset(180),
    energy_input_kwh: energyInput,
    metered_output_kwh: metered,
    estimated_technical_loss_kwh: technical,
    unexplained_loss_kwh: unexplained,
    unexplained_loss_ratio: ratio,
    customer_count: 18 + Math.floor(rng() * 30),
    risk_tier: riskTierForScore(score),
    risk_score: round(score, 1),
    waterfall: [
      { label: "Energy input", value: energyInput, kind: "input" },
      { label: "Metered output", value: metered, kind: "deduction" },
      { label: "Technical loss", value: technical, kind: "deduction" },
      { label: "Unexplained", value: unexplained, kind: "residual" },
    ],
    currency: DEMO_CURRENCY,
    estimated_loss_value: round(unexplained * ENERGY_PRICE_PER_KWH, 0),
  };
}

export function buildLossTrend(): LossTrend {
  const rng = makeRng(40000);
  const points: LossTrend["points"] = [];
  for (let m = 0; m < 12; m++) {
    const input = round(120000 + rng() * 18000, 0);
    const technical = round(input * 0.045, 0);
    const unexplained = round(input * (0.03 + (m / 11) * 0.02 + rng() * 0.004), 0);
    const metered = round(input - technical - unexplained, 0);
    points.push({
      timestamp: isoFromDayOffset(m * 30),
      energy_input_kwh: input,
      metered_output_kwh: metered,
      technical_loss_kwh: technical,
      unexplained_loss_kwh: unexplained,
    });
  }
  return { unit: "kWh", points };
}

function buildModels(): ModelRegistryEntry[] {
  return [
    {
      id: "model-2025-06",
      model_version: MODEL_VERSION,
      feature_version: FEATURE_VERSION,
      algorithm: "gradient_boosting",
      trained_at: isoFromDayOffset(176),
      metrics: { pr_auc: 0.81, precision_at_k: 0.74, k: 100, recall_at_k: 0.43, brier: 0.09 },
      is_active: true,
      notes: "Active production model. Calibrated with isotonic regression.",
    },
    {
      id: "model-2025-03",
      model_version: "risk-gbm-2025.03.2",
      feature_version: "features-2025.03.0",
      algorithm: "gradient_boosting",
      trained_at: isoFromDayOffset(80),
      metrics: { pr_auc: 0.76, precision_at_k: 0.69, k: 100, recall_at_k: 0.38, brier: 0.11 },
      is_active: false,
      notes: "Previous baseline.",
    },
  ];
}

/** Deterministically assign a risk score for a customer index. */
function scoreForIndex(index: number): number {
  if (index === 1) return 87;
  const rng = makeRng(50000 + index);
  const roll = rng();
  if (roll > 0.96) return round(70 + rng() * 18, 1);
  if (roll > 0.86) return round(50 + rng() * 19, 1);
  if (roll > 0.66) return round(30 + rng() * 19, 1);
  return round(rng() * 29, 1);
}

function buildDataset(): DemoDataset {
  const transformers: GridAsset[] = [];
  for (let i = 1; i <= TRANSFORMER_COUNT; i++) {
    const region = regionForIndex(i - 1);
    const rng = makeRng(60000 + i);
    const isCritical = i === 1;
    const score = isCritical ? 88 : round(rng() * 62, 1);
    transformers.push(
      transformerFactory({
        index: i,
        regionId: region.id,
        riskScore: score,
        geometry: {
          type: "Point",
          coordinates: [
            round(region.center[0] + (rng() - 0.5) * 0.02, 6),
            round(region.center[1] + (rng() - 0.5) * 0.02, 6),
          ],
        },
      })
    );
  }

  const customers: Customer[] = [];
  const riskScores = new Map<string, RiskScore>();
  const readings = new Map<string, CustomerReadings>();
  const peerComparison = new Map<string, PeerComparisonPoint[]>();
  const lossAttribution = new Map<string, number>();

  for (let i = 1; i <= CUSTOMER_COUNT; i++) {
    const transformer = transformers[(i - 1) % TRANSFORMER_COUNT]!;
    const region = DEMO_REGIONS.find((r) => r.id === transformer.region_id) ?? regionForIndex(i);
    const rng = makeRng(70000 + i);
    const score = scoreForIndex(i);
    const isCritical = i === 1;
    const id = `cust-${pad(i, 4)}`;
    const customer = customerFactory({
      index: i,
      transformerId: transformer.id,
      regionId: region.id,
      riskScore: score,
      geometry: {
        type: "Point",
        coordinates: [
          round(region.center[0] + (rng() - 0.5) * 0.03, 6),
          round(region.center[1] + (rng() - 0.5) * 0.025, 6),
        ],
      },
    });
    customers.push(customer);

    const baseDaily = round(6 + rng() * 18, 2);
    const anomaly = score >= 70;
    readings.set(id, buildReadings(id, baseDaily, anomaly));
    peerComparison.set(id, buildPeerComparison(baseDaily, anomaly));

    const estLossKwh = isCritical ? 3120 : round((score / 100) * 3600, 0);
    riskScores.set(
      id,
      riskScoreFactory({
        entityId: id,
        entityType: "customer",
        score,
        estimatedLossKwh: estLossKwh,
        estimatedLossValue: round(estLossKwh * ENERGY_PRICE_PER_KWH, 0),
        confidence: isCritical ? 0.82 : round(0.55 + (score / 100) * 0.4, 2),
      })
    );
    lossAttribution.set(id, isCritical ? 0.34 : round((score / 100) * 0.2, 3));
  }

  const reconciliations = new Map<string, TransformerReconciliation>();
  transformers.forEach((tx, idx) => {
    reconciliations.set(tx.id, buildReconciliation(tx, idx + 1));
    riskScores.set(
      tx.id,
      riskScoreFactory({
        entityId: tx.id,
        entityType: "transformer",
        score: tx.risk_score ?? 0,
        estimatedLossKwh: reconciliations.get(tx.id)!.unexplained_loss_kwh,
        estimatedLossValue: reconciliations.get(tx.id)!.estimated_loss_value,
      })
    );
  });

  const dataset: DemoDataset = {
    operator: DEMO_OPERATOR,
    regions: DEMO_REGIONS,
    transformers,
    customers,
    riskScores,
    reconciliations,
    readings,
    peerComparison,
    lossAttribution,
    models: buildModels(),
    missions: [],
    cases: [],
    outcomes: [],
  };

  seedInspections(dataset);
  return dataset;
}

function seedInspections(dataset: DemoDataset): void {
  const mission: InspectionMission = {
    id: "mission-0001",
    name: "Jordaan — Week 24 sweep",
    region_id: "region-jordaan",
    status: "in_progress",
    scheduled_date: isoFromDayOffset(182),
    assigned_team_id: "team-alpha",
    route_geometry: null,
    estimated_total_value: 1180,
    currency: DEMO_CURRENCY,
    created_by: "demo-operator",
    created_at: isoFromDayOffset(181),
    case_count: 2,
  };
  dataset.missions.push(mission);

  dataset.cases.push(
    inspectionFactory({
      id: "case-0001",
      missionId: mission.id,
      customerId: CRITICAL_CUSTOMER_ID,
      index: 1,
      status: "assigned",
      recommendedAction: "On-site inspection: suspected unmetered load",
      notes: "Highest-priority case. Requires field confirmation before any action.",
    })
  );
  dataset.cases.push(
    inspectionFactory({
      id: "case-0002",
      missionId: mission.id,
      customerId: "cust-0014",
      index: 2,
      status: "scheduled",
      recommendedAction: "Meter diagnostics: suspected CT/meter fault — verify metering chain",
      notes: "Pattern consistent with meter under-registration, not theft.",
    })
  );
}

let dataset: DemoDataset = buildDataset();

export function getDemoDataset(): DemoDataset {
  return dataset;
}

export function resetDemoData(): void {
  dataset = buildDataset();
}

export function buildDashboardSummary(data: DemoDataset = dataset): DashboardSummary {
  const tiers: RiskTier[] = ["LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL"];
  const counts = new Map<RiskTier, number>(tiers.map((t) => [t, 0]));
  let unexplained = 0;
  let lossValue = 0;
  for (const customer of data.customers) {
    const tier = customer.risk_tier ?? "LOW";
    counts.set(tier, (counts.get(tier) ?? 0) + 1);
    const risk = data.riskScores.get(customer.id);
    if (risk) {
      unexplained += risk.estimated_loss_kwh;
      lossValue += risk.estimated_loss_value;
    }
  }
  return {
    total_customers: 1000,
    total_transformers: data.transformers.length,
    total_unexplained_loss_kwh: round(unexplained, 0),
    total_estimated_loss_value: round(lossValue, 0),
    currency: DEMO_CURRENCY,
    period_start: isoFromDayOffset(150),
    period_end: isoFromDayOffset(180),
    high_risk_count: counts.get("HIGH") ?? 0,
    critical_risk_count: counts.get("CRITICAL") ?? 0,
    open_inspections: data.cases.filter((c) => c.status !== "resolved" && c.status !== "dismissed")
      .length,
    risk_tier_breakdown: tiers.map((tier) => ({ tier, count: counts.get(tier) ?? 0 })),
    model_version: MODEL_VERSION,
    feature_version: FEATURE_VERSION,
  };
}

export {
  CRITICAL_CUSTOMER_ID,
  CRITICAL_TRANSFORMER_ID,
  CUSTOMER_COUNT,
  ENERGY_PRICE_PER_KWH,
  TRANSFORMER_COUNT,
};
