import type { LineString } from "./geojson";

export type MissionStatus = "draft" | "planned" | "in_progress" | "completed" | "cancelled";
export type CaseStatus =
  | "queued"
  | "assigned"
  | "scheduled"
  | "in_progress"
  | "resolved"
  | "dismissed";
export type InspectionOutcomeType =
  | "confirmed_theft"
  | "confirmed_meter_fault"
  | "no_issue_found"
  | "inconclusive";

export interface InspectionQueueItem {
  customer_id: string;
  external_ref: string;
  risk_score: number;
  risk_tier: string;
  inspection_priority: number;
  estimated_loss_kwh: number;
  estimated_loss_value: number;
  currency: string;
  recommended_action: string;
  region_name: string | null;
}

export interface InspectionMission {
  id: string;
  name: string;
  region_id: string | null;
  status: MissionStatus;
  scheduled_date: string | null;
  assigned_team_id: string | null;
  route_geometry: LineString | null;
  estimated_total_value: number;
  currency: string;
  created_by: string;
  created_at: string;
  case_count: number;
}

export interface InspectionCase {
  id: string;
  mission_id: string;
  customer_id: string;
  risk_score_id: string | null;
  status: CaseStatus;
  priority_rank: number;
  scheduled_at: string | null;
  assigned_to: string | null;
  recommended_action: string | null;
  notes: string | null;
}

export interface InspectionOutcome {
  id: string;
  inspection_case_id: string;
  outcome: InspectionOutcomeType;
  confirmed_loss_type: string | null;
  estimated_recovered_kwh: number | null;
  estimated_recovered_value: number | null;
  evidence: Record<string, unknown>;
  submitted_by: string;
  submitted_at: string;
}

export interface CreateMissionRequest {
  name: string;
  region_id?: string | null;
  scheduled_date?: string | null;
  assigned_team_id?: string | null;
}

export interface CreateCaseRequest {
  customer_id: string;
  risk_score_id?: string | null;
  recommended_action?: string | null;
  notes?: string | null;
}

export interface UpdateCaseRequest {
  status?: CaseStatus;
  assigned_to?: string | null;
  scheduled_at?: string | null;
  notes?: string | null;
}

export interface SubmitOutcomeRequest {
  outcome: InspectionOutcomeType;
  confirmed_loss_type?: string | null;
  estimated_recovered_kwh?: number | null;
  estimated_recovered_value?: number | null;
  evidence?: Record<string, unknown>;
}

export interface RouteRequest {
  customer_ids: string[];
}

export interface RouteResponse {
  ordered_customer_ids: string[];
  route_geometry: LineString;
  total_distance_km: number;
}
