import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../../styles/app-tokens.css";
import "../../../styles/app-typescale.css";
import { Button } from "../Button";
import { CheckboxGroup } from "./CheckboxGroup";
import { Fieldset } from "./Fieldset";
import { Form } from "./Form";
import { NumberField } from "./NumberField";
import { OtpField } from "./OtpField";
import { Slider } from "./Slider";
import { Switch } from "./Switch";
import { Toggle } from "./Toggle";
import { ToggleGroup } from "./ToggleGroup";

const meta = {
  title: "Production/Design System/Base UI/Advanced Form Controls",
  tags: ["status-production"],
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const CheckboxGroupExample: Story = {
  render: () => (
    <CheckboxGroup
      label="Project focus"
      description="Select one or more themes."
      defaultValue={["planning"]}
      options={[
        { value: "planning", label: "Planning", description: "Organize upcoming work" },
        { value: "reviews", label: "Reviews", description: "Check saved decisions" },
        { value: "reports", label: "Reports", description: "Summarize recent activity" },
      ]}
    />
  ),
};

export const FieldsetExample: Story = {
  render: () => (
    <Fieldset legend="Display settings" description="These preferences apply to each view.">
      <Switch label="Show labels" defaultChecked />
      <Switch label="Enable animation" />
    </Fieldset>
  ),
};

export const FormExample: Story = {
  render: () => (
    <Form aria-label="Example form" onFormSubmit={() => undefined}>
      <NumberField label="Daily goal" defaultValue={10} min={1} max={100} />
      <Button type="submit">Save goal</Button>
    </Form>
  ),
};

export const NumberFieldExample: Story = {
  render: () => (
    <NumberField
      label="Processing limit"
      description="Higher values may take longer to complete."
      defaultValue={18}
      min={1}
      max={40}
    />
  ),
};

export const OtpFieldExample: Story = {
  render: () => (
    <OtpField
      label="Verification code"
      description="Enter the six digits sent to your device."
      length={6}
    />
  ),
};

export const SliderExample: Story = {
  render: () => (
    <div style={{ width: "20rem" }}>
      <Slider label="Value range" defaultValue={[-3, 3]} min={-10} max={10} />
    </div>
  ),
};

export const SwitchExample: Story = {
  render: () => (
    <Switch
      label="Continue automatically"
      description="Continue to the next step after the current task is complete."
      defaultChecked
    />
  ),
};

export const ToggleExample: Story = {
  render: () => <Toggle defaultPressed>Pin item</Toggle>,
};

export const ToggleGroupExample: Story = {
  render: () => (
    <ToggleGroup
      aria-label="Display options"
      defaultValue={["arrows"]}
      multiple
      options={[
        { value: "arrows", label: "Arrows" },
        { value: "squares", label: "Squares" },
        { value: "coordinates", label: "Coordinates" },
      ]}
    />
  ),
};
