import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="No data" description="Nothing here yet" />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("Nothing here yet")).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("surfaces an Error message and renders an alert role", () => {
    render(<ErrorState error={new Error("boom")} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
  });
});
