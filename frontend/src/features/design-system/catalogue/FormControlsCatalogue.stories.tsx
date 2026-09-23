import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { Button } from "../Button";
import { Autocomplete } from "../form-controls/Autocomplete";
import { Combobox } from "../form-controls/Combobox";
import { Field } from "../form-controls/Field";
import { RadioGroup } from "../form-controls/RadioGroup";
import { Select } from "../form-controls/Select";
import { TextInput } from "../form-controls/TextInput";
import type { DropdownOptionDefinition } from "../form-controls/private/DropdownParts";
import { storyViewport } from "../../../storybook/viewports";
import { catalogueDemoShell } from "./catalogueDemoShell";
import { DemoRow } from "./FamilyPage";
import { FormControlsCatalogueDocs } from "./FormControlsCatalogueDocs";
import styles from "./catalogue.module.css";

const meta = {
  title: "Reference/Catalogue/Actions and Form Controls",
  tags: ["status-reference"],
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta;

export default meta;

type Story = StoryObj<typeof meta>;

const OPTIONS: DropdownOptionDefinition[] = [
  { value: "categories", label: "Categories" },
  { value: "collections", label: "Collections" },
  { value: "recent", label: "Recent items" },
  {
    value: "rich-option",
    label: "Rich option",
    disabled: true,
    content: {
      primary: "Rich option",
      secondary: "option with secondary copy",
      trailing: "E60",
    },
  },
];

const RADIO_OPTIONS = [
  { value: "first", label: "First option" },
  { value: "second", label: "Second option", description: "Suggested from your selection" },
];

function ControlledSelectHarness() {
  const [value, setValue] = useState<string | null>("collections");
  return (
    <Select ariaLabel="Processing mode" options={OPTIONS} value={value} onValueChange={setValue} />
  );
}

function ControlledSelectLoadingHarness() {
  const [value, setValue] = useState<string | null>(null);
  return (
    <Select
      ariaLabel="Loading processing mode"
      options={OPTIONS}
      loading
      value={value}
      onValueChange={setValue}
    />
  );
}

function ControlledSelectEmptyHarness() {
  const [value, setValue] = useState<string | null>(null);
  return (
    <Select
      ariaLabel="Empty processing mode"
      options={[]}
      emptyContent="No analysis modes found."
      value={value}
      onValueChange={setValue}
    />
  );
}

function ControlledComboboxHarness() {
  const [value, setValue] = useState<string | null>(null);
  return (
    <Combobox ariaLabel="Category search" options={OPTIONS} value={value} onValueChange={setValue} />
  );
}

function ControlledAutocompleteHarness() {
  const [value, setValue] = useState<string>("collections");
  return (
    <Autocomplete
      ariaLabel="Category suggestion"
      options={OPTIONS}
      value={value}
      onValueChange={setValue}
    />
  );
}

export const Docs: Story = {
  render: () => <FormControlsCatalogueDocs />,
};

export const FieldStates: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Default with a description">
          <Field
            label="Processing mode"
            description="Choose how items should be processed."
            htmlFor="catalogue-description-input"
          >
            <TextInput id="catalogue-description-input" aria-label="Processing mode" />
          </Field>
        </DemoRow>
        <DemoRow caption="Required with mark">
          <Field label="Collection name" required htmlFor="catalogue-required-input">
            <TextInput id="catalogue-required-input" aria-label="Collection name" />
          </Field>
        </DemoRow>
        <DemoRow caption="Invalid with visible error text">
          <Field
            label="Reference code"
            htmlFor="catalogue-invalid-input"
            invalid
            error="Enter a valid reference code."
          >
            <TextInput id="catalogue-invalid-input" invalid value="invalid-code" readOnly />
          </Field>
        </DemoRow>
        <DemoRow caption="Disabled">
          <Field label="Reference code" htmlFor="catalogue-disabled-input" disabled>
            <TextInput id="catalogue-disabled-input" disabled />
          </Field>
        </DemoRow>
      </div>,
    ),
};

export const TextInputStates: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Default">
          <div className={styles.demoControlWrap}>
            <TextInput aria-label="Default text input" />
          </div>
        </DemoRow>
        <DemoRow caption="Search type with leading icon and trailing action">
          <div className={styles.demoControlWrap}>
            <TextInput
              type="search"
              aria-label="Search source"
              leading={
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="M15.5 15.5 21 21" stroke="currentColor" strokeWidth="2" />
                </svg>
              }
              trailing={<Button size="sm">Filter</Button>}
            />
          </div>
        </DemoRow>
        <DemoRow caption="Invalid">
          <div className={styles.demoControlWrap}>
            <TextInput aria-label="Invalid input example" invalid value="invalid-code" readOnly />
          </div>
        </DemoRow>
        <DemoRow caption="Disabled">
          <div className={styles.demoControlWrap}>
            <TextInput aria-label="Disabled input example" disabled />
          </div>
        </DemoRow>
      </div>,
    ),
};

export const SelectStates: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Default (interactive: open, choose, clear of the popup)">
          <div className={styles.demoControlWrap}>
            <ControlledSelectHarness />
          </div>
        </DemoRow>
        <DemoRow caption="Disabled">
          <div className={styles.demoControlWrap}>
            <Select
              ariaLabel="Disabled select"
              options={OPTIONS}
              value="collections"
              onValueChange={() => undefined}
              disabled
            />
          </div>
        </DemoRow>
        <DemoRow caption="Read-only">
          <div className={styles.demoControlWrap}>
            <Select
              ariaLabel="Read-only select"
              options={OPTIONS}
              value="collections"
              onValueChange={() => undefined}
              readOnly
            />
          </div>
        </DemoRow>
      </div>,
    ),
};

export const SelectLoadingAndEmpty: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Loading (options replaced by a loading message in the popup)">
          <div className={styles.demoControlWrap}>
            <ControlledSelectLoadingHarness />
          </div>
        </DemoRow>
        <DemoRow caption="Empty (popup shows the caller's empty message)">
          <div className={styles.demoControlWrap}>
            <ControlledSelectEmptyHarness />
          </div>
        </DemoRow>
      </div>,
    ),
};

export const ComboboxStates: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Default (interactive: type to filter, clear, or choose an option)">
          <div className={styles.demoControlWrap}>
            <ControlledComboboxHarness />
          </div>
        </DemoRow>
        <DemoRow caption="Loading">
          <div className={styles.demoControlWrap}>
            <Combobox
              ariaLabel="Loading combobox"
              options={OPTIONS}
              loading
              value={null}
              onValueChange={() => undefined}
            />
          </div>
        </DemoRow>
        <DemoRow caption="Disabled with a selected value">
          <div className={styles.demoControlWrap}>
            <Combobox
              ariaLabel="Disabled combobox"
              options={OPTIONS}
              value="collections"
              disabled
              onValueChange={() => undefined}
            />
          </div>
        </DemoRow>
      </div>,
    ),
};

export const AutocompleteStates: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Default (interactive: pick a suggestion or keep typing)">
          <div className={styles.demoControlWrap}>
            <ControlledAutocompleteHarness />
          </div>
        </DemoRow>
        <DemoRow caption="Loading">
          <div className={styles.demoControlWrap}>
            <Autocomplete
              ariaLabel="Loading autocomplete"
              options={OPTIONS}
              loading
              value=""
              onValueChange={() => undefined}
            />
          </div>
        </DemoRow>
        <DemoRow caption="Disabled">
          <div className={styles.demoControlWrap}>
            <Autocomplete
              ariaLabel="Disabled autocomplete"
              options={OPTIONS}
              value="collections"
              disabled
              onValueChange={() => undefined}
            />
          </div>
        </DemoRow>
      </div>,
    ),
};

export const RadioGroupStates: Story = {
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Segmented (selected: First option)">
          <RadioGroup
            ariaLabel="Subject side segmented"
            appearance="segmented"
            options={RADIO_OPTIONS.slice(0, 2)}
            value="first"
            onValueChange={() => undefined}
          />
        </DemoRow>
        <DemoRow caption="Stacked with descriptions and one disabled option">
          <RadioGroup
            ariaLabel="Subject side stacked"
            appearance="stacked"
            options={RADIO_OPTIONS.map((option, index) =>
              index === 1 ? { ...option, disabled: true } : option,
            )}
            value="second"
            onValueChange={() => undefined}
          />
        </DemoRow>
        <DemoRow caption="Disabled group">
          <RadioGroup
            ariaLabel="Disabled subject side"
            options={RADIO_OPTIONS.slice(0, 2)}
            value="first"
            disabled
            onValueChange={() => undefined}
          />
        </DemoRow>
      </div>,
    ),
};

export const NarrowViewport: Story = {
  parameters: storyViewport("constrained-412"),
  render: () =>
    catalogueDemoShell(
      <div className={styles.demoStack}>
        <DemoRow caption="Field with required TextInput at the constrained width">
          <Field label="Collection name" required htmlFor="catalogue-narrow-input">
            <TextInput id="catalogue-narrow-input" aria-label="Narrow collection name" />
          </Field>
        </DemoRow>
        <DemoRow caption="Select at the constrained width (opens a popup)">
          <ControlledSelectHarness />
        </DemoRow>
        <DemoRow caption="Segmented RadioGroup at the constrained width">
          <RadioGroup
            ariaLabel="Narrow subject side"
            options={RADIO_OPTIONS.slice(0, 2)}
            value="first"
            onValueChange={() => undefined}
          />
        </DemoRow>
      </div>,
    ),
};
