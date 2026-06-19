import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InspectionStatusBadge } from "@/components/inspection-status-badge";

describe("InspectionStatusBadge", () => {
  it("renders human-readable labels for case statuses", () => {
    render(<InspectionStatusBadge status="in_progress" />);
    expect(screen.getByText("In progress")).toBeInTheDocument();
  });

  it("renders resolved status", () => {
    render(<InspectionStatusBadge status="resolved" />);
    expect(screen.getByText("Resolved")).toBeInTheDocument();
  });
});
