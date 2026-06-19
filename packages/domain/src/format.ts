import type { Currency, Locale } from "@gridtrace/config";

const DEFAULT_LOCALE: Locale = "en-US";

/** Format an energy quantity in kWh / MWh with explicit units. */
export function formatEnergyKwh(kwh: number, locale: Locale = DEFAULT_LOCALE): string {
  if (Math.abs(kwh) >= 1_000_000) {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(kwh / 1_000_000)} GWh`;
  }
  if (Math.abs(kwh) >= 1_000) {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(kwh / 1_000)} MWh`;
  }
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(kwh)} kWh`;
}

export function formatCurrency(
  value: number,
  currency: Currency = "EUR",
  locale: Locale = DEFAULT_LOCALE
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(ratio: number, locale: Locale = DEFAULT_LOCALE): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(ratio);
}

export function formatNumber(value: number, locale: Locale = DEFAULT_LOCALE): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
}

/** Format an ISO 8601 UTC timestamp for display. */
export function formatDateTime(iso: string, locale: Locale = DEFAULT_LOCALE): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(iso));
}

export function formatDate(iso: string, locale: Locale = DEFAULT_LOCALE): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(iso)
  );
}

/** Signed delta with a leading +/-, for MetricDelta components. */
export function formatSignedPercent(ratio: number, locale: Locale = DEFAULT_LOCALE): string {
  const sign = ratio > 0 ? "+" : "";
  return `${sign}${formatPercent(ratio, locale)}`;
}
