import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { OutcomeTrack } from "./OutcomeTrack";

afterEach(cleanup);

describe("OutcomeTrack", () => {
  it("renders outcome shares that fill the track", () => {
    render(
      <OutcomeTrack
        values={{ wins: 7, draws: 2, losses: 3 }}
        accessibleLabel="7 completed, 2 unchanged, 3 blocked"
      />,
    );

    const track = screen.getByRole("img", { name: "7 completed, 2 unchanged, 3 blocked" });
    expect(track).toBeVisible();
    expect(track.children).toHaveLength(3);
  });

  it("omits the unknown segment when unknown is absent", () => {
    const { container } = render(
      <OutcomeTrack
        values={{ wins: 50, draws: 25, losses: 25 }}
        accessibleLabel="Task outcomes"
      />,
    );

    expect(container.querySelector("[class*='unknown']")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Task outcomes" }).children).toHaveLength(3);
  });

  it("keeps unknown items inside the total with an accurate accessible label", () => {
    const { container } = render(
      <OutcomeTrack
        values={{ wins: 7, draws: 2, losses: 3, unknown: 2 }}
        accessibleLabel="7 completed, 2 unchanged, 3 blocked, 2 unknown"
      />,
    );

    const track = screen.getByRole("img", { name: "7 completed, 2 unchanged, 3 blocked, 2 unknown" });
    expect(track.children).toHaveLength(4);
    const unknownSegment = container.querySelector("[class*='unknown']") as HTMLElement;
    expect(unknownSegment).toBeInTheDocument();
    // 2 of 14 total items keeps the accurate share.
    expect(unknownSegment.style.inlineSize).toContain("14.28");
  });

  it("renders an empty total without negative widths", () => {
    render(<OutcomeTrack values={{ wins: 0, draws: 0, losses: 0 }} accessibleLabel="No items" />);

    const track = screen.getByRole("img", { name: "No items" });
    expect(track).toBeVisible();
    for (const segment of Array.from(track.children)) {
      expect((segment as HTMLElement).style.inlineSize).toBe("0%");
    }
  });
});
