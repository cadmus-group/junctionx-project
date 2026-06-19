import type { CaseStatus, MissionStatus } from "@gridtrace/contracts";
import { Badge } from "@gridtrace/ui";

type Status = CaseStatus | MissionStatus;

const VARIANT: Record<Status, "default" | "secondary" | "success" | "warning" | "info" | "danger"> =
  {
    draft: "secondary",
    planned: "info",
    queued: "secondary",
    assigned: "info",
    scheduled: "info",
    in_progress: "warning",
    completed: "success",
    resolved: "success",
    dismissed: "secondary",
    cancelled: "danger",
  };

const LABEL: Record<Status, string> = {
  draft: "Draft",
  planned: "Planned",
  queued: "Queued",
  assigned: "Assigned",
  scheduled: "Scheduled",
  in_progress: "In progress",
  completed: "Completed",
  resolved: "Resolved",
  dismissed: "Dismissed",
  cancelled: "Cancelled",
};

export function InspectionStatusBadge({ status }: { status: Status }) {
  return <Badge variant={VARIANT[status] ?? "secondary"}>{LABEL[status] ?? status}</Badge>;
}
