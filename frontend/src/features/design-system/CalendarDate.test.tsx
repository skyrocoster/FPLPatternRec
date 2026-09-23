import * as axe from "axe-core";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import axeMatchers from "@chialab/vitest-axe";

import { CalendarDate, type CalendarDateValue } from "./CalendarDate";
import {
  formatUtcDate,
  getUtcCalendarDay,
  isFutureUtcDate,
  normalizeToUtcMidnight,
  toUtcMidnight,
  type UtcCalendarDay,
} from "./CalendarDateUtils";

expect.extend(axeMatchers);

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function Harness({ initialValue = null }: { initialValue?: CalendarDateValue }) {
  const [value, setValue] = useState<CalendarDateValue>(initialValue);

  return (
    <>
      <CalendarDate value={value} onChange={setValue} />
      <output data-testid="value">{value ? value.toISOString() : "blank"}</output>
    </>
  );
}

const JANUARY_2025 = new Date("2025-01-15T00:00:00.000Z");

describe("UTC calendar helpers", () => {
  it("reads UTC calendar parts across a local-day boundary", () => {
    const lateUtc = new Date("2025-01-15T23:30:00.000Z");
    const earlyUtc = new Date("2025-01-16T00:30:00.000Z");

    expect(getUtcCalendarDay(lateUtc)).toEqual({ year: 2025, month: 0, day: 15 });
    expect(getUtcCalendarDay(earlyUtc)).toEqual({ year: 2025, month: 0, day: 16 });
  });

  it("normalizes a selected calendar tuple to canonical UTC midnight", () => {
    const day: UtcCalendarDay = { year: 2025, month: 0, day: 15 };

    expect(toUtcMidnight(day).toISOString()).toBe("2025-01-15T00:00:00.000Z");
    expect(normalizeToUtcMidnight(new Date("2025-01-15T23:59:59.999Z")).toISOString()).toBe(
      "2025-01-15T00:00:00.000Z",
    );
    expect(formatUtcDate(new Date("2025-01-15T23:59:59.999Z"))).toBe("2025-01-15");
  });

  it("compares UTC calendar tuples, keeping today selectable", () => {
    const now = new Date("2025-01-15T23:59:59.999Z");

    expect(isFutureUtcDate(new Date("2025-01-15T00:00:00.000Z"), now)).toBe(false);
    expect(isFutureUtcDate(new Date("2025-01-16T00:00:00.000Z"), now)).toBe(true);
    expect(isFutureUtcDate(new Date("2024-12-31T23:59:59.999Z"), now)).toBe(false);
  });
});

describe("CalendarDate", () => {
  it("starts blank and exposes a controlled accessible trigger", () => {
    render(<Harness />);

    const trigger = screen.getByRole("button", { name: "Date: Choose date" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("value")).toHaveTextContent("blank");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the Base UI Popover and restores focus when closed", async () => {
    const user = userEvent.setup();
    render(<Harness initialValue={JANUARY_2025} />);

    const trigger = screen.getByRole("button", { name: "Date: 2025-01-15" });
    await user.click(trigger);

    const dialog = await screen.findByRole("dialog", { name: "Date" });
    expect(within(dialog).getByRole("heading", { name: "Date" })).toBeVisible();
    expect(within(dialog).getByRole("grid")).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("emits a canonical UTC-midnight value when a day is selected", async () => {
    const user = userEvent.setup();
    render(<Harness initialValue={JANUARY_2025} />);

    await user.click(screen.getByRole("button", { name: "Date: 2025-01-15" }));
    const dialog = screen.getByRole("dialog", { name: "Date" });
    await user.click(within(dialog).getByRole("button", { name: /January 20th, 2025/ }));

    expect(screen.getByTestId("value")).toHaveTextContent("2025-01-20T00:00:00.000Z");
    expect(screen.getByRole("button", { name: "Date: 2025-01-20" })).toBeVisible();
  });

  it("keeps the current UTC day selectable and disables later UTC days", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2025-01-15T23:59:59.999Z"));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Harness initialValue={JANUARY_2025} />);

    await user.click(screen.getByRole("button", { name: "Date: 2025-01-15" }));
    const dialog = await screen.findByRole("dialog", { name: "Date" });
    const today = within(dialog).getByRole("button", { name: /January 15th, 2025/ });
    const tomorrow = within(dialog).getByRole("button", { name: /January 16th, 2025/ });

    expect(today).not.toBeDisabled();
    expect(tomorrow).toBeDisabled();
  });

  it("returns to blank through the clear seam", async () => {
    const user = userEvent.setup();
    render(<Harness initialValue={JANUARY_2025} />);

    await user.click(screen.getByRole("button", { name: "Date: 2025-01-15" }));
    const dialog = await screen.findByRole("dialog", { name: "Date" });
    await user.click(within(dialog).getByRole("button", { name: "Clear date" }));

    expect(screen.getByTestId("value")).toHaveTextContent("blank");
    expect(screen.getByRole("button", { name: "Date: Choose date" })).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("passes validation attributes through to the trigger", () => {
    render(
      <>
        <CalendarDate
          value={JANUARY_2025}
          onChange={() => undefined}
          label="Start date"
          invalid
          describedBy="filters-error"
          triggerId="start-date-trigger"
        />
        <p id="filters-error">Start date must be on or before end date.</p>
      </>,
    );

    const trigger = screen.getByRole("button", { name: "Start date: 2025-01-15" });
    expect(trigger).toHaveAttribute("id", "start-date-trigger");
    expect(trigger).toHaveAttribute("aria-invalid", "true");
    expect(trigger).toHaveAttribute("aria-describedby", "filters-error");
  });

  it("passes a focused axe check for the Popover dialog", async () => {
    const user = userEvent.setup();
    render(<Harness initialValue={JANUARY_2025} />);

    await user.click(screen.getByRole("button", { name: "Date: 2025-01-15" }));
    const dialog = await screen.findByRole("dialog", { name: "Date" });

    expect(await axe.run(dialog)).toHaveNoViolations();
  });
});
