import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { riskTierForScore } from "@gridtrace/domain";
import { RiskBadge } from "./risk-badge";
import { ConfidenceBadge, confidenceLabel } from "./confidence-badge";

describe("RiskBadge", () => {
  it("renders the tier label and score", () => {
    render(<RiskBadge tier="CRITICAL" score={87} />);
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("87")).toBeInTheDocument();
  });

  it("maps boundary scores to the tier shown", () => {
    expect(riskTierForScore(85)).toBe("CRITICAL");
    render(<RiskBadge tier={riskTierForScore(70)} showScore={false} />);
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("hides score when showScore is false", () => {
    render(<RiskBadge tier="LOW" score={10} showScore={false} />);
    expect(screen.queryByText("10")).not.toBeInTheDocument();
  });
});

describe("ConfidenceBadge", () => {
  it("derives qualitative labels from thresholds", () => {
    expect(confidenceLabel(0.9)).toBe("High");
    expect(confidenceLabel(0.6)).toBe("Moderate");
    expect(confidenceLabel(0.2)).toBe("Low");
  });

  it("renders a clamped percentage", () => {
    render(<ConfidenceBadge confidence={1.4} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});
