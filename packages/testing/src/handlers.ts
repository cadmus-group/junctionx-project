import type {
  AssetCustomerSummary,
  AuthLoginResponse,
  Customer,
  CustomerRiskProfile,
  GridAsset,
  HealthResponse,
  InspectionCase,
  InspectionMission,
  InspectionOutcome,
  InspectionQueueItem,
  Page,
  ProblemDetail,
  RouteResponse,
} from "@gridtrace/contracts";
import { http, HttpResponse } from "msw";
import {
  buildDashboardSummary,
  buildLossTrend,
  ENERGY_PRICE_PER_KWH,
  getDemoDataset,
} from "./data";
import { customersGeoJson, hotspotsGeoJson } from "./geojson";
import { inspectionQueueItemFactory } from "./factories";
import { isoFromDayOffset, pad, round } from "./seed";

const V1 = "*/api/v1";

function paginate<T>(items: T[], url: URL): Page<T> {
  const page = Math.max(1, Number(url.searchParams.get("page") ?? "1"));
  const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? "25"));
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
  };
}

function problem(status: number, title: string, detail?: string) {
  const body: ProblemDetail = { type: "about:blank", title, status, detail };
  return HttpResponse.json(body, { status });
}

let missionSeq = 100;
let caseSeq = 100;
let outcomeSeq = 100;

export const handlers = [
  http.post(`${V1}/auth/login`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as { email?: string };
    const response: AuthLoginResponse = {
      access_token: "demo-token",
      token_type: "bearer",
      expires_in: 3600,
      user: {
        id: "demo-operator",
        email: body.email ?? "operator@gridtrace.demo",
        name: "Demo Operator",
        role: "analyst",
      },
    };
    return HttpResponse.json(response);
  }),

  http.get(`${V1}/dashboard/summary`, () => HttpResponse.json(buildDashboardSummary())),

  http.get(`${V1}/dashboard/loss-trend`, () => HttpResponse.json(buildLossTrend())),

  http.get(`${V1}/gis/anomalies/geojson`, ({ request }) => {
    const url = new URL(request.url);
    const minRisk = Number(url.searchParams.get("min_risk") ?? "0");
    return HttpResponse.json(customersGeoJson(getDemoDataset(), minRisk));
  }),

  http.get(`${V1}/gis/hotspots`, ({ request }) => {
    const url = new URL(request.url);
    const minRisk = Number(url.searchParams.get("min_risk") ?? "0");
    return HttpResponse.json(hotspotsGeoJson(getDemoDataset(), minRisk));
  }),

  http.get(`${V1}/assets/transformers/:id/reconciliation`, ({ params }) => {
    const data = getDemoDataset();
    const recon = data.reconciliations.get(String(params.id));
    if (!recon) return problem(404, "Transformer not found", `No transformer ${params.id}`);
    return HttpResponse.json(recon);
  }),

  http.get(`${V1}/assets/:id/customers`, ({ params, request }) => {
    const data = getDemoDataset();
    const url = new URL(request.url);
    const downstream = data.customers.filter((c) => c.transformer_id === String(params.id));
    const summaries: AssetCustomerSummary[] = downstream
      .map((c) => ({
        customer_id: c.id,
        external_ref: c.external_ref,
        customer_type: c.customer_type,
        risk_score: c.risk_score,
        risk_tier: c.risk_tier,
        estimated_loss_kwh: data.riskScores.get(c.id)?.estimated_loss_kwh ?? null,
      }))
      .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
    return HttpResponse.json(paginate(summaries, url));
  }),

  http.get(`${V1}/assets/:id`, ({ params }) => {
    const data = getDemoDataset();
    const asset = data.transformers.find((t) => t.id === String(params.id));
    if (!asset) return problem(404, "Asset not found", `No asset ${params.id}`);
    return HttpResponse.json(asset);
  }),

  http.get(`${V1}/assets`, ({ request }) => {
    const data = getDemoDataset();
    const url = new URL(request.url);
    const q = url.searchParams.get("q")?.toLowerCase();
    const assetType = url.searchParams.get("asset_type");
    let assets: GridAsset[] = [...data.transformers];
    if (assetType) assets = assets.filter((a) => a.asset_type === assetType);
    if (q) assets = assets.filter((a) => a.name.toLowerCase().includes(q) || a.external_id.toLowerCase().includes(q));
    assets.sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
    return HttpResponse.json(paginate(assets, url));
  }),

  http.get(`${V1}/customers/:id/readings`, ({ params }) => {
    const data = getDemoDataset();
    const readings = data.readings.get(String(params.id));
    if (!readings) return problem(404, "Customer not found", `No customer ${params.id}`);
    return HttpResponse.json(readings);
  }),

  http.get(`${V1}/customers/:id/risk-profile`, ({ params }) => {
    const data = getDemoDataset();
    const id = String(params.id);
    const customer = data.customers.find((c) => c.id === id);
    const risk = data.riskScores.get(id);
    if (!customer || !risk) return problem(404, "Customer not found", `No customer ${id}`);
    const profile: CustomerRiskProfile = {
      customer,
      risk,
      peer_comparison: data.peerComparison.get(id) ?? [],
      loss_attribution_share: data.lossAttribution.get(id) ?? 0,
      notes: [
        "This is a model-generated risk indicator, not a determination of wrongdoing.",
        "On-site human inspection is required before any action.",
        "Alternative explanations include meter faults, estimation gaps, or recent occupancy changes.",
      ],
    };
    return HttpResponse.json(profile);
  }),

  http.get(`${V1}/customers/:id`, ({ params }) => {
    const data = getDemoDataset();
    const customer = data.customers.find((c) => c.id === String(params.id));
    if (!customer) return problem(404, "Customer not found", `No customer ${params.id}`);
    return HttpResponse.json(customer);
  }),

  http.get(`${V1}/customers`, ({ request }) => {
    const data = getDemoDataset();
    const url = new URL(request.url);
    const minRisk = url.searchParams.get("min_risk");
    const tier = url.searchParams.get("tier");
    const q = url.searchParams.get("q")?.toLowerCase();
    let customers: Customer[] = [...data.customers];
    if (minRisk) customers = customers.filter((c) => (c.risk_score ?? 0) >= Number(minRisk));
    if (tier) customers = customers.filter((c) => c.risk_tier === tier);
    if (q) customers = customers.filter((c) => c.external_ref.toLowerCase().includes(q));
    customers.sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
    return HttpResponse.json(paginate(customers, url));
  }),

  http.get(`${V1}/inspections/queue`, ({ request }) => {
    const data = getDemoDataset();
    const url = new URL(request.url);
    const regionId = url.searchParams.get("region_id");
    const items: InspectionQueueItem[] = data.customers
      .filter((c) => (c.risk_score ?? 0) >= 50)
      .filter((c) => !regionId || c.region_id === regionId)
      .map((c) => {
        const risk = data.riskScores.get(c.id);
        const region = data.regions.find((r) => r.id === c.region_id);
        return inspectionQueueItemFactory({
          customerId: c.id,
          externalRef: c.external_ref,
          score: c.risk_score ?? 0,
          estimatedLossKwh: risk?.estimated_loss_kwh,
          estimatedLossValue: risk?.estimated_loss_value,
          regionName: region?.name ?? null,
          recommendedAction: risk?.explanations.some((e) => e.feature === "meter_event_count")
            ? "Verify meter integrity and check for tamper events on-site"
            : "On-site inspection to confirm and explain unexplained consumption",
        });
      })
      .sort((a, b) => b.inspection_priority - a.inspection_priority);
    return HttpResponse.json(paginate(items, url));
  }),

  http.post(`${V1}/inspections/missions`, async ({ request }) => {
    const data = getDemoDataset();
    const body = (await request.json()) as {
      name: string;
      region_id?: string | null;
      scheduled_date?: string | null;
      assigned_team_id?: string | null;
    };
    const mission: InspectionMission = {
      id: `mission-${pad(++missionSeq, 4)}`,
      name: body.name,
      region_id: body.region_id ?? null,
      status: "draft",
      scheduled_date: body.scheduled_date ?? null,
      assigned_team_id: body.assigned_team_id ?? null,
      route_geometry: null,
      estimated_total_value: 0,
      currency: "EUR",
      created_by: "demo-operator",
      created_at: isoFromDayOffset(183),
      case_count: 0,
    };
    data.missions.push(mission);
    return HttpResponse.json(mission, { status: 201 });
  }),

  http.post(`${V1}/inspections/missions/:id/cases`, async ({ params, request }) => {
    const data = getDemoDataset();
    const missionId = String(params.id);
    const mission = data.missions.find((m) => m.id === missionId);
    if (!mission) return problem(404, "Mission not found", `No mission ${missionId}`);
    const body = (await request.json()) as {
      customer_id: string;
      risk_score_id?: string | null;
      recommended_action?: string | null;
      notes?: string | null;
    };
    const newCase: InspectionCase = {
      id: `case-${pad(++caseSeq, 4)}`,
      mission_id: missionId,
      customer_id: body.customer_id,
      risk_score_id: body.risk_score_id ?? `risk-${body.customer_id}`,
      status: "queued",
      priority_rank: data.cases.filter((c) => c.mission_id === missionId).length + 1,
      scheduled_at: null,
      assigned_to: null,
      recommended_action: body.recommended_action ?? "On-site inspection",
      notes: body.notes ?? null,
    };
    data.cases.push(newCase);
    mission.case_count += 1;
    const risk = data.riskScores.get(body.customer_id);
    if (risk) mission.estimated_total_value = round(mission.estimated_total_value + risk.estimated_loss_value, 0);
    return HttpResponse.json(newCase, { status: 201 });
  }),

  http.patch(`${V1}/inspections/cases/:id`, async ({ params, request }) => {
    const data = getDemoDataset();
    const found = data.cases.find((c) => c.id === String(params.id));
    if (!found) return problem(404, "Case not found", `No case ${params.id}`);
    const body = (await request.json()) as Partial<InspectionCase>;
    Object.assign(found, {
      status: body.status ?? found.status,
      assigned_to: body.assigned_to ?? found.assigned_to,
      scheduled_at: body.scheduled_at ?? found.scheduled_at,
      notes: body.notes ?? found.notes,
    });
    return HttpResponse.json(found);
  }),

  http.post(`${V1}/inspections/cases/:id/outcome`, async ({ params, request }) => {
    const data = getDemoDataset();
    const caseId = String(params.id);
    const found = data.cases.find((c) => c.id === caseId);
    if (!found) return problem(404, "Case not found", `No case ${caseId}`);
    const body = (await request.json()) as {
      outcome: InspectionOutcome["outcome"];
      confirmed_loss_type?: string | null;
      estimated_recovered_kwh?: number | null;
      estimated_recovered_value?: number | null;
      evidence?: Record<string, unknown>;
    };
    const recoveredKwh = body.estimated_recovered_kwh ?? null;
    const outcome: InspectionOutcome = {
      id: `outcome-${pad(++outcomeSeq, 4)}`,
      inspection_case_id: caseId,
      outcome: body.outcome,
      confirmed_loss_type: body.confirmed_loss_type ?? null,
      estimated_recovered_kwh: recoveredKwh,
      estimated_recovered_value:
        body.estimated_recovered_value ??
        (recoveredKwh != null ? round(recoveredKwh * ENERGY_PRICE_PER_KWH, 0) : null),
      evidence: body.evidence ?? {},
      submitted_by: "demo-operator",
      submitted_at: isoFromDayOffset(184),
    };
    data.outcomes.push(outcome);
    found.status = "resolved";
    return HttpResponse.json(outcome, { status: 201 });
  }),

  http.post(`${V1}/inspections/route`, async ({ request }) => {
    const data = getDemoDataset();
    const body = (await request.json()) as { customer_ids: string[] };
    const coords = body.customer_ids
      .map((id) => data.customers.find((c) => c.id === id)?.geometry?.coordinates)
      .filter((c): c is [number, number] => Array.isArray(c)) as [number, number][];
    let distance = 0;
    for (let i = 1; i < coords.length; i++) {
      const [x1, y1] = coords[i - 1]!;
      const [x2, y2] = coords[i]!;
      distance += Math.hypot(x2 - x1, y2 - y1) * 111;
    }
    const response: RouteResponse = {
      ordered_customer_ids: body.customer_ids,
      route_geometry: { type: "LineString", coordinates: coords },
      total_distance_km: round(distance, 2),
    };
    return HttpResponse.json(response);
  }),

  http.get(`${V1}/models`, () => HttpResponse.json(getDemoDataset().models)),

  http.get(`${V1}/health`, () => {
    const response: HealthResponse = {
      status: "ok",
      version: "demo",
      database: "ok",
      demo_mode: true,
      time: isoFromDayOffset(184),
    };
    return HttpResponse.json(response);
  }),
];
