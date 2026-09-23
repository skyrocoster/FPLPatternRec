import * as axe from "axe-core";
import axeMatchers from "@chialab/vitest-axe";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Autocomplete } from "./Autocomplete";
import { Combobox } from "./Combobox";
import { Field } from "./Field";
import { RadioGroup } from "./RadioGroup";
import { Select } from "./Select";
import { TextInput } from "./TextInput";
import type { DropdownOptionDefinition } from "./private/DropdownParts";

expect.extend(axeMatchers);

beforeEach(() => {
  vi.stubGlobal("PointerEvent", MouseEvent);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const OPTIONS: readonly DropdownOptionDefinition[] = [
  { value: "priority", label: "High priority" },
  {
    value: "standard",
    label: "Standard priority",
    customBody: <span aria-hidden="true">Priority: standard</span>,
  },
  { value: "deferred", label: "Deferred", disabled: true },
];

function ControlledCombobox({
  onChange = () => undefined,
}: {
  onChange?: (value: string | null) => void;
}) {
  const [value, setValue] = useState<string | null>(null);
  return (
    <Combobox
      ariaLabel="Priority"
      options={OPTIONS}
      value={value}
      onValueChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
}

describe("reusable form controls", () => {
  it("associates externally supplied Field presentation without owning validation timing", () => {
    render(
      <Field
        label="Email"
        description="Used for reminders."
        required
        invalid
        error="Email is incomplete."
      >
        <TextInput aria-label="Email" type="email" invalid defaultValue="learner@" />
      </Field>,
    );

    const input = screen.getByRole("textbox", { name: "Email" });
    expect(input).toHaveAttribute("aria-describedby");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Used for reminders.")).toBeVisible();
    expect(screen.getByText("Email is incomplete.")).toBeVisible();
  });

  it("keeps TextInput to the approved text-like types and forwards slots and states", () => {
    render(
      <TextInput
        aria-label="Search"
        type="search"
        leading={<span>lead</span>}
        trailing={<span>trail</span>}
        readOnly
      />,
    );
    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveAttribute("readonly");
    expect(screen.getByText("lead")).toBeVisible();
    expect(screen.getByText("trail")).toBeVisible();
  });

  it("commits only listed Combobox values with Base UI keyboard behavior", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ControlledCombobox onChange={onChange} />);

    const input = screen.getByRole("combobox", { name: "Priority" });
    await user.click(input);
    await user.type(input, "Standard");
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onChange).toHaveBeenLastCalledWith("standard");
    expect(input).toHaveValue("Standard priority");
  });

  it("forwards clicks from an already-focused Combobox input", async () => {
    const user = userEvent.setup();
    const onInputClick = vi.fn();
    render(
      <Combobox
        ariaLabel="Priority"
        onInputClick={onInputClick}
        onValueChange={() => undefined}
        options={OPTIONS}
        value={null}
      />,
    );

    const input = screen.getByRole("combobox", { name: "Priority" });
    await user.click(input);
    await user.click(input);

    expect(onInputClick).toHaveBeenCalledTimes(2);
  });

  it("uses the required plain label for custom option accessibility and filtering", async () => {
    const user = userEvent.setup();
    render(<ControlledCombobox />);
    const input = screen.getByRole("combobox", { name: "Priority" });
    await user.click(input);
    await user.type(input, "Standard");

    const option = screen.getByRole("option", { name: "Standard priority" });
    expect(option).toBeVisible();
    expect(within(option).getByText("Priority: standard")).toBeVisible();
  });

  it("keeps Autocomplete free-form instead of requiring a listed value", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [value, setValue] = useState("");
      return (
        <>
          <Autocomplete
            ariaLabel="Session name"
            options={OPTIONS}
            value={value}
            onValueChange={setValue}
          />
          <output>{value}</output>
        </>
      );
    }
    render(<Harness />);
    await user.type(screen.getByRole("combobox", { name: "Session name" }), "My custom session");
    expect(screen.getByText("My custom session")).toBeVisible();
  });

  it("Select exposes selected and disabled option semantics", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(
      <Select
        ariaLabel="Priority choice"
        options={OPTIONS}
        value="priority"
        onValueChange={onValueChange}
      />,
    );
    await user.click(screen.getByRole("combobox", { name: "Priority choice" }));

    expect(screen.getByRole("option", { name: "High priority" })).toHaveAttribute(
      "data-selected",
    );
    expect(screen.getByRole("option", { name: "Deferred" })).toHaveAttribute("data-disabled");
  });

  it("RadioGroup preserves one selection and supports explicit appearances", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [value, setValue] = useState("both");
      return (
        <RadioGroup
          appearance="stacked"
          ariaLabel="Side"
          options={[
            { value: "both", label: "Both" },
            { value: "priority", label: "Priority" },
          ]}
       value={value}
          onValueChange={setValue}
        />
      );
    }
    render(<Harness />);
    const priority = screen.getByRole("radio", { name: "Priority" });
    priority.focus();
    await user.keyboard(" ");
    expect(priority).toBeChecked();
    await user.keyboard(" ");
    expect(priority).toBeChecked();
  });

  it("passes a focused accessibility check with field and control semantics", async () => {
    const { container } = render(
      <Field label="Priority" description="Choose one priority level.">
        <ControlledCombobox />
      </Field>,
    );
    await userEvent.setup().click(screen.getByRole("combobox", { name: "Priority" }));
    expect(await axe.run(screen.getByRole("listbox"))).toHaveNoViolations();
    expect(await axe.run(container)).toHaveNoViolations();
  });
});
