/**
 * Shared, timezone-safe calendar helpers for the date pickers.
 *
 * Every value is handled at UTC midnight so the displayed day never drifts with
 * the viewer's timezone.
 */
export const MS_DAY = 86_400_000;

export const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

export const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function utcDay(d: Date): Date {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
}

/** Parse an ISO string or a YYYY-MM-DD value to a UTC-midnight day. */
export function parseIso(iso?: string): Date | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? undefined : utcDay(d);
}

export function todayUtc(): Date {
  const n = new Date();
  return new Date(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate()));
}

export function addDays(d: Date, n: number): Date {
  return new Date(d.getTime() + n * MS_DAY);
}

export function startOfMonth(d: Date): Date {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1));
}

export function addMonths(d: Date, n: number): Date {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + n, 1));
}

export function sameDay(a?: Date, b?: Date): boolean {
  return !!a && !!b && a.getTime() === b.getTime();
}

/** Short label, e.g. "20 Jun". */
export function fmtShort(d: Date): string {
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]!.slice(0, 3)}`;
}

/** Full label, e.g. "20 Jun 2026". */
export function fmtFull(d: Date): string {
  return `${fmtShort(d)} ${d.getUTCFullYear()}`;
}

/** YYYY-MM-DD value (date-only, as used by form fields). */
export function toDateValue(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** 6 weeks of days (Monday-first) covering the given month view. */
export function buildGrid(view: Date): Date[] {
  const first = startOfMonth(view);
  const offset = (first.getUTCDay() + 6) % 7; // 0 = Monday
  const start = addDays(first, -offset);
  return Array.from({ length: 42 }, (_, i) => addDays(start, i));
}
