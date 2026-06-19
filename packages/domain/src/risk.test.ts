import { describe, expect, it } from "vitest";
import { riskTierForScore } from "./risk";

describe("riskTierForScore", () => {
  it("maps boundary values to the correct tier", () => {
    expect(riskTierForScore(0)).toBe("LOW");
    expect(riskTierForScore(29)).toBe("LOW");
    expect(riskTierForScore(30)).toBe("WATCH");
    expect(riskTierForScore(49)).toBe("WATCH");
    expect(riskTierForScore(50)).toBe("MEDIUM");
    expect(riskTierForScore(69)).toBe("MEDIUM");
    expect(riskTierForScore(70)).toBe("HIGH");
    expect(riskTierForScore(84)).toBe("HIGH");
    expect(riskTierForScore(85)).toBe("CRITICAL");
    expect(riskTierForScore(100)).toBe("CRITICAL");
  });

  it("clamps out-of-range scores", () => {
    expect(riskTierForScore(-10)).toBe("LOW");
    expect(riskTierForScore(150)).toBe("CRITICAL");
  });
});
