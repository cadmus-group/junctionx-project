import type { InspectionCase, InspectionOutcome } from "@gridtrace/contracts";
import type { QueryClient } from "@tanstack/react-query";

/**
 * The API exposes write endpoints for cases/outcomes but no list-by-mission
 * read, so created cases are tracked in the query cache for the session. This
 * keeps all network writes flowing through @gridtrace/api-client mutations.
 */
export function caseListKey(missionId: string) {
  return ["inspections", "mission", missionId, "cases"] as const;
}

export function appendCaseToCache(
  queryClient: QueryClient,
  missionId: string,
  inspectionCase: InspectionCase
): void {
  queryClient.setQueryData<InspectionCase[]>(caseListKey(missionId), (prev) => [
    ...(prev ?? []),
    inspectionCase,
  ]);
}

export function applyOutcomeToCache(
  queryClient: QueryClient,
  missionId: string,
  outcome: InspectionOutcome
): void {
  queryClient.setQueryData<InspectionCase[]>(caseListKey(missionId), (prev) =>
    (prev ?? []).map((c) =>
      c.id === outcome.inspection_case_id ? { ...c, status: "resolved" } : c
    )
  );
}
