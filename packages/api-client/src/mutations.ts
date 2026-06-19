import type {
  CreateCaseRequest,
  CreateMissionRequest,
  InspectionCase,
  InspectionMission,
  InspectionOutcome,
  RouteRequest,
  RouteResponse,
  SubmitOutcomeRequest,
  UpdateCaseRequest,
} from "@gridtrace/contracts";
import type { GridTraceClient } from "./client";

const V1 = "api/v1";

/** Inspection write operations. Pair these with TanStack `useMutation`. */
export function inspectionMutations(client: GridTraceClient) {
  return {
    createMission: (body: CreateMissionRequest) =>
      client.request<InspectionMission>(`${V1}/inspections/missions`, {
        method: "POST",
        body,
      }),
    addCase: (missionId: string, body: CreateCaseRequest) =>
      client.request<InspectionCase>(`${V1}/inspections/missions/${missionId}/cases`, {
        method: "POST",
        body,
      }),
    updateCase: (caseId: string, body: UpdateCaseRequest) =>
      client.request<InspectionCase>(`${V1}/inspections/cases/${caseId}`, {
        method: "PATCH",
        body,
      }),
    submitOutcome: (caseId: string, body: SubmitOutcomeRequest) =>
      client.request<InspectionOutcome>(`${V1}/inspections/cases/${caseId}/outcome`, {
        method: "POST",
        body,
      }),
    route: (body: RouteRequest) =>
      client.request<RouteResponse>(`${V1}/inspections/route`, { method: "POST", body }),
  };
}
