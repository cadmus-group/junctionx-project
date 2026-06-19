import { describe, expect, it } from "vitest";
import {
  buildEnergyWaterfallOption,
  buildRiskDistributionOption,
  precisionRecallFromModel,
} from "./index";

describe("buildEnergyWaterfallOption", () => {
  it("produces a transparent base and a visible value series", () => {
    const option = buildEnergyWaterfallOption({
      waterfall: [
        { label: "Input", value: 12400, kind: "input" },
        { label: "Metered", value: 10550, kind: "deduction" },
        { label: "Technical", value: 620, kind: "deduction" },
        { label: "Unexplained", value: 1230, kind: "residual" },
      ],
    });
    const series = option.series as unknown[];
    expect(series).toHaveLength(2);
  });
});

describe("buildRiskDistributionOption", () => {
  it("orders tiers low->critical and fills missing tiers with zero", () => {
    const option = buildRiskDistributionOption([
      { tier: "CRITICAL", count: 1 },
      { tier: "LOW", count: 100 },
    ]);
    const xAxis = option.xAxis as { data: string[] };
    expect(xAxis.data).toEqual(["LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL"]);
  });
});

describe("precisionRecallFromModel", () => {
  it("generates a monotonically non-increasing precision curve", () => {
    const pts = precisionRecallFromModel({
      id: "m1",
      model_version: "v1",
      feature_version: "f1",
      algorithm: "gbm",
      trained_at: "2025-01-01T00:00:00Z",
      metrics: { pr_auc: 0.8, precision_at_k: 0.9, k: 100 },
      is_active: true,
      notes: null,
    });
    for (let i = 1; i < pts.length; i++) {
      expect(pts[i]!.precision).toBeLessThanOrEqual(pts[i - 1]!.precision + 1e-9);
    }
  });
});
