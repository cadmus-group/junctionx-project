import { describe, expect, it } from "vitest";
import {
  buildDashboardSummary,
  CRITICAL_CUSTOMER_ID,
  CRITICAL_TRANSFORMER_ID,
  getDemoDataset,
} from "./data";
import { customerFactory, transformerFactory } from "./factories";

describe("demo dataset", () => {
  it("contains the showcase critical transformer reconciliation", () => {
    const recon = getDemoDataset().reconciliations.get(CRITICAL_TRANSFORMER_ID)!;
    expect(recon.energy_input_kwh).toBe(12400);
    expect(recon.metered_output_kwh).toBe(10550);
    expect(recon.estimated_technical_loss_kwh).toBe(620);
    expect(recon.unexplained_loss_kwh).toBe(1230);
    expect(recon.unexplained_loss_ratio).toBeCloseTo(0.0992, 4);
    expect(recon.risk_tier).toBe("CRITICAL");
  });

  it("has exactly one critical customer with score 87", () => {
    const data = getDemoDataset();
    const critical = data.customers.find((c) => c.id === CRITICAL_CUSTOMER_ID)!;
    expect(critical.risk_score).toBe(87);
    expect(critical.risk_tier).toBe("CRITICAL");
  });

  it("seeds a meter-fault inspection case recommending diagnostics", () => {
    const data = getDemoDataset();
    const meterFault = data.cases.find((c) =>
      c.recommended_action?.toLowerCase().includes("meter diagnostics")
    );
    expect(meterFault).toBeDefined();
  });

  it("builds a consistent dashboard summary", () => {
    const summary = buildDashboardSummary();
    expect(summary.currency).toBe("EUR");
    expect(summary.total_transformers).toBe(10);
    expect(summary.critical_risk_count).toBeGreaterThanOrEqual(1);
  });
});

describe("factories are deterministic", () => {
  it("produces identical customers for the same index", () => {
    expect(customerFactory({ index: 5 })).toEqual(customerFactory({ index: 5 }));
  });

  it("produces identical transformers for the same index", () => {
    expect(transformerFactory({ index: 3 })).toEqual(transformerFactory({ index: 3 }));
  });
});
