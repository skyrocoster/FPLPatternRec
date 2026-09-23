import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { useState, type ReactNode } from "react";

import { CalendarDate, type CalendarDateProps, type CalendarDateValue } from "./CalendarDate";
import { getUtcCalendarDay, toUtcMidnight, type UtcCalendarDay } from "./CalendarDateUtils";
import { storyViewport } from "../../storybook/viewports";

const meta = {
  title: "Production/Design System/Components/Calendar Date",
  tags: ["status-production"],
  component: CalendarDate,
  args: {
    value: null,
    onChange: fn(),
    label: "Date",
  },
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof CalendarDate>;

export default meta;
type Story = StoryObj<typeof meta>;

const JANUARY_15_2025 = new Date("2025-01-15T00:00:00.000Z");

function shell(children: ReactNode) {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--app-spacing-24)",
        padding: "var(--app-spacing-32)",
        minHeight: "100vh",
        backgroundColor: "var(--md-sys-color-surface)",
        color: "var(--md-sys-color-on-surface)",
        fontFamily: "system-ui",
      }}
    >
      <div style={{ maxInlineSize: "32rem" }}>{children}</div>
    </main>
  );
}

interface CalendarFixtureProps {
  initialValue?: CalendarDateValue;
  label?: string;
  onChange?: CalendarDateProps["onChange"];
}

function CalendarFixture({
  initialValue = null,
  label = "Date",
  onChange = () => undefined,
}: CalendarFixtureProps) {
  const [value, setValue] = useState<CalendarDateValue>(initialValue);

  const handleChange = (nextValue: CalendarDateValue) => {
    setValue(nextValue);
    onChange(nextValue);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--app-spacing-12)" }}>
      <CalendarDate value={value} onChange={handleChange} label={label} />
      <p
        style={{
          margin: 0,
          color: "var(--md-sys-color-on-surface-variant)",
          fontSize: "var(--md-sys-typescale-body-medium-size)",
        }}
      >
        UTC value:{" "}
        <output data-testid="calendar-date-value">{value ? value.toISOString() : "blank"}</output>
      </p>
    </div>
  );
}

function renderCalendar(args: CalendarDateProps) {
  return shell(
    <CalendarFixture initialValue={args.value} onChange={args.onChange} label={args.label} />,
  );
}

function currentMonthFixture(args: CalendarDateProps) {
  const today = getUtcCalendarDay(new Date());
  const initialValue = toUtcMidnight({
    year: today.year,
    month: today.month,
    day: Math.min(today.day, 15),
  });

  return shell(
    <CalendarFixture initialValue={initialValue} onChange={args.onChange} label={args.label} />,
  );
}

function ordinalSuffix(day: number) {
  if (day % 100 >= 11 && day % 100 <= 13) return "th";
  if (day % 10 === 1) return "st";
  if (day % 10 === 2) return "nd";
  if (day % 10 === 3) return "rd";
  return "th";
}

function calendarDayName(day: UtcCalendarDay) {
  const monthName = new Intl.DateTimeFormat("en-US", {
    month: "long",
    timeZone: "UTC",
  }).format(toUtcMidnight({ ...day, day: 1 }));

  return new RegExp(`${monthName} ${day.day}${ordinalSuffix(day.day)}, ${day.year}`);
}

export const Blank: Story = {
  name: "Blank — effective now until selected",
  render: renderCalendar,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    const trigger = canvas.getByRole("button", { name: "Date: Choose date" });

    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(trigger);

    const dialog = await body.findByRole("dialog", { name: "Date" });
    await expect(within(dialog).getByRole("heading", { name: "Date" })).toBeVisible();
    await expect(within(dialog).getByRole("grid")).toBeVisible();
    await expect(within(dialog).getByRole("button", { name: "Clear date" })).toBeDisabled();

    await userEvent.keyboard("{Escape}");
    await waitFor(() =>
      expect(body.queryByRole("dialog", { name: "Date" })).not.toBeInTheDocument(),
    );
    await expect(trigger).toHaveFocus();
  },
};

export const Selected: Story = {
  name: "Selected — canonical UTC date",
  args: { value: JANUARY_15_2025 },
  render: renderCalendar,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    const trigger = canvas.getByRole("button", { name: "Date: 2025-01-15" });

    await expect(canvas.getByTestId("calendar-date-value")).toHaveTextContent(
      "2025-01-15T00:00:00.000Z",
    );
    await userEvent.click(trigger);

    const dialog = await body.findByRole("dialog", { name: "Date" });
    await expect(
      within(dialog).getByRole("button", {
        name: calendarDayName({ year: 2025, month: 0, day: 15 }),
      }),
    ).toBeVisible();
    await expect(within(dialog).getByRole("button", { name: "Clear date" })).toBeEnabled();
  },
};

export const CurrentDayAndFutureDisabled: Story = {
  name: "Current UTC day selectable, future UTC days disabled",
  render: currentMonthFixture,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(canvas.getByRole("button", { name: /Date:/ }));

    const dialog = await body.findByRole("dialog", { name: "Date" });
    const today = getUtcCalendarDay(new Date());
    const todayButton = within(dialog).getByRole("button", { name: calendarDayName(today) });

    await expect(todayButton).toBeEnabled();

    const disabledDateButtons = Array.from(
      dialog.querySelectorAll<HTMLButtonElement>("button[disabled]"),
    ).filter((button) => button.closest("[data-day]"));

    // On the final UTC day of a month there is no later date in the rendered month.
    if (disabledDateButtons.length > 0) {
      await expect(disabledDateButtons[0]).toBeDisabled();
    }
  },
};

export const Clearable: Story = {
  name: "Clear — return to blank",
  args: { value: JANUARY_15_2025 },
  render: renderCalendar,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(canvas.getByRole("button", { name: "Date: 2025-01-15" }));

    const dialog = await body.findByRole("dialog", { name: "Date" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Clear date" }));

    await expect(canvas.getByTestId("calendar-date-value")).toHaveTextContent("blank");
    await expect(canvas.getByRole("button", { name: "Date: Choose date" })).toBeVisible();
    await expect(body.queryByRole("dialog", { name: "Date" })).not.toBeInTheDocument();
  },
};

export const KeyboardAndFocus: Story = {
  name: "Keyboard selection and focus restoration",
  args: { value: JANUARY_15_2025 },
  render: renderCalendar,
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    const trigger = canvas.getByRole("button", { name: "Date: 2025-01-15" });
    await userEvent.click(trigger);

    const dialog = await body.findByRole("dialog", { name: "Date" });
    const selectedDay = within(dialog).getByRole("button", {
      name: calendarDayName({ year: 2025, month: 0, day: 15 }),
    });
    await userEvent.tab();
    await userEvent.tab();
    await expect(selectedDay).toHaveFocus();

    await userEvent.keyboard("{ArrowRight}");
    const nextDay = within(dialog).getByRole("button", {
      name: calendarDayName({ year: 2025, month: 0, day: 16 }),
    });
    await expect(nextDay).toHaveFocus();
    await userEvent.keyboard("{Enter}");

    await expect(args.onChange).toHaveBeenCalledWith(new Date("2025-01-16T00:00:00.000Z"));
    await waitFor(() =>
      expect(body.queryByRole("dialog", { name: "Date" })).not.toBeInTheDocument(),
    );
    await expect(canvas.getByRole("button", { name: "Date: 2025-01-16" })).toHaveFocus();
  },
};

export const Constrained: Story = {
  name: "Constrained viewport",
  args: { value: JANUARY_15_2025 },
  parameters: storyViewport("constrained-412"),
  render: renderCalendar,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(canvas.getByRole("button", { name: "Date: 2025-01-15" }));
    await expect(body.findByRole("dialog", { name: "Date" })).resolves.toBeVisible();
  },
};

export const ForcedColors: Story = {
  name: "Forced-colors token fallback",
  args: { value: JANUARY_15_2025 },
  parameters: {
    docs: {
      description: {
        story:
          "Review the open calendar with forced-colors browser emulation to verify the local token fallback.",
      },
    },
  },
  render: renderCalendar,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(canvas.getByRole("button", { name: "Date: 2025-01-15" }));
    await expect(body.findByRole("dialog", { name: "Date" })).resolves.toBeVisible();
  },
};
