/**
 * Role model for the operator console — the three "Përdoruesit Kryesorë" from
 * the Innovation4Albania NTL-detection brief.
 *
 * Every role shares the same application shell; the role changes which sections
 * appear in the sidebar (the "view") and where the user lands after sign-in.
 *
 *  - operator  → Energy Distribution Operator: oversight, money, priorities.
 *  - analyst   → Analytical & Operational Teams: model triage, explainability.
 *  - inspector → Field Inspection Teams: assigned inspections on the ground.
 */
export type Role = "operator" | "analyst" | "inspector";

export const ROLES: Role[] = ["operator", "analyst", "inspector"];

export const ROLE_LABELS: Record<Role, string> = {
  operator: "Distribution Operator",
  analyst: "Analyst Team",
  inspector: "Field Inspector",
};

/** One-line description of each role's remit (shown in the profile menu). */
export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  operator: "Oversight, losses & inspection ROI",
  analyst: "Risk triage, explainability & cases",
  inspector: "Assigned field inspections",
};

/** Narrow an arbitrary backend role string to a known Role (defaults to analyst). */
export function resolveRole(raw: string | undefined | null): Role {
  if (raw === "admin") return "operator"; // backward-compat with earlier sessions
  return ROLES.includes(raw as Role) ? (raw as Role) : "analyst";
}

/** Where each role lands after sign-in — their primary workspace. */
export const ROLE_HOME: Record<Role, string> = {
  operator: "/",
  analyst: "/",
  inspector: "/inspections",
};

/**
 * Demo credentials surfaced for reference. In demo mode any password is
 * accepted; the username selects the role (see the mock auth handler).
 */
export const DEMO_CREDENTIALS: { username: string; role: Role }[] = [
  { username: "operator", role: "operator" },
  { username: "analyst", role: "analyst" },
  { username: "inspector", role: "inspector" },
];
