/**
 * Role model for the operator console.
 *
 * Every role shares the same application shell (top bar, main content area,
 * the map and its tooling). Roles only change which navigation entries — and
 * therefore which sections — are exposed in the sidebar.
 */
export type Role = "admin" | "analyst" | "inspector";

export const ROLES: Role[] = ["admin", "analyst", "inspector"];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrator",
  analyst: "Data Analyst",
  inspector: "Field Inspector",
};

/** Narrow an arbitrary backend role string to a known Role (defaults to analyst). */
export function resolveRole(raw: string | undefined | null): Role {
  return ROLES.includes(raw as Role) ? (raw as Role) : "analyst";
}

/**
 * Demo credentials surfaced on the login screen. In demo mode any password is
 * accepted; the username selects the role (see the mock auth handler).
 */
export const DEMO_CREDENTIALS: { username: string; role: Role }[] = [
  { username: "admin", role: "admin" },
  { username: "analyst", role: "analyst" },
  { username: "inspector", role: "inspector" },
];
