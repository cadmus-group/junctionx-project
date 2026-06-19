import {
  filtersFromSearchParams,
  filtersToSearchParams,
} from "@gridtrace/domain";
import { describe, expect, it } from "vitest";

describe("global filter serialization", () => {
  it("round-trips filters through URL search params", () => {
    const params = filtersToSearchParams({
      regionId: "region-jordaan",
      minRisk: 70,
      tier: "CRITICAL",
      selected: "cust-0001",
    });
    const parsed = filtersFromSearchParams(params);
    expect(parsed.regionId).toBe("region-jordaan");
    expect(parsed.minRisk).toBe(70);
    expect(parsed.tier).toBe("CRITICAL");
    expect(parsed.selected).toBe("cust-0001");
  });

  it("omits empty values when serializing", () => {
    const params = filtersToSearchParams({ regionId: undefined, minRisk: undefined });
    expect(params.toString()).toBe("");
  });
});
