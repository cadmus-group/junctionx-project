import { describe, expect, it } from "vitest";
import { fitBoundsToGeometry } from "../geometry";
import { riskScoreRgba, riskTierRgba } from "../style";

describe("fitBoundsToGeometry", () => {
  it("computes bounds for a feature collection of points", () => {
    const bounds = fitBoundsToGeometry({
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "Point", coordinates: [4.9, 52.3] }, properties: {} },
        { type: "Feature", geometry: { type: "Point", coordinates: [5.1, 52.5] }, properties: {} },
      ],
    });
    expect(bounds).toEqual([
      [4.9, 52.3],
      [5.1, 52.5],
    ]);
  });

  it("returns null for empty input", () => {
    expect(fitBoundsToGeometry(null)).toBeNull();
  });
});

describe("risk color mapping", () => {
  it("returns a red-dominant color for high scores and green for low", () => {
    const high = riskScoreRgba(95);
    const low = riskScoreRgba(5);
    expect(high[0]).toBeGreaterThan(high[1]);
    expect(low[1]).toBeGreaterThan(low[0]);
  });

  it("falls back to a neutral color when tier is null", () => {
    expect(riskTierRgba(null)).toEqual([139, 152, 165, 160]);
  });
});
