import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ProgressMeter } from "./ProgressMeter";

afterEach(cleanup);

describe("ProgressMeter", () => {
  it("renders a determinate meter with value text", () => {
    render(<ProgressMeter value={75} label="Task completion" valueText="75%" />);

    const meter = screen.getByRole("meter", { name: "Task completion" });
    expect(meter).toHaveAttribute("aria-valuemin", "0");
    expect(meter).toHaveAttribute("aria-valuemax", "100");
    expect(meter).toHaveAttribute("aria-valuenow", "75");
    expect(meter).toHaveAttribute("aria-valuetext", "75%");
  });

  it("clamps values above max and below min", () => {
    const { rerender } = render(<ProgressMeter value={150} label="Coverage" />);
    expect(screen.getByRole("meter", { name: "Coverage" })).toHaveAttribute("aria-valuenow", "100");

    rerender(<ProgressMeter value={-20} label="Coverage" />);
    expect(screen.getByRole("meter", { name: "Coverage" })).toHaveAttribute("aria-valuenow", "0");
  });

  it("renders unavailable data without a meter contract", () => {
    render(<ProgressMeter value={null} label="Available items" valueText="No coverage data" />);

    expect(screen.queryByRole("meter")).not.toBeInTheDocument();
    expect(screen.getByText("No coverage data")).toBeVisible();
  });
});
