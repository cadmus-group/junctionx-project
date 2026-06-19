/** Deterministic PRNG so demo data is identical on every run. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const DEMO_SEED = 42;

export function makeRng(seed: number = DEMO_SEED): () => number {
  return mulberry32(seed);
}

export function randomInt(rng: () => number, min: number, max: number): number {
  return Math.floor(rng() * (max - min + 1)) + min;
}

export function pick<T>(rng: () => number, items: readonly T[]): T {
  return items[Math.floor(rng() * items.length)] as T;
}

export function round(value: number, decimals = 2): number {
  const f = 10 ** decimals;
  return Math.round(value * f) / f;
}

export function pad(value: number, width: number): string {
  return String(value).padStart(width, "0");
}

/** Stable ISO timestamp generator anchored to a fixed demo epoch. */
const DEMO_EPOCH = Date.UTC(2025, 0, 1, 0, 0, 0);

export function isoFromDayOffset(dayOffset: number): string {
  return new Date(DEMO_EPOCH + dayOffset * 86_400_000).toISOString();
}

export function isoFromHourOffset(hourOffset: number): string {
  return new Date(DEMO_EPOCH + hourOffset * 3_600_000).toISOString();
}
