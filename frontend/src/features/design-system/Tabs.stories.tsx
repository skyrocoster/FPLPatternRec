import { expect, userEvent, within } from "storybook/test";
import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";

import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import { Tabs, type TabDefinition } from "./Tabs";

const meta = {
  title: "Production/Design System/Components/Tabs",
  tags: ["status-production"],
  component: Tabs,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: "var(--md-sys-color-surface)",
          color: "var(--md-sys-color-on-surface)",
          fontFamily: "system-ui",
        }}
      >
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Tabs>;

export default meta;
type Story = StoryObj<typeof meta>;

function OverviewPanel() {
  return (
    <div
      style={{
        display: "inline-flex",
        padding: "var(--app-spacing-8)",
        backgroundColor: "var(--md-sys-color-surface-container-high)",
        color: "var(--md-sys-color-on-surface)",
      }}
    >
      <input aria-label="Overview field" />
    </div>
  );
}

function DetailsPanel() {
  return <progress aria-label="Details progress" max={1} value={0.5} />;
}

function NotesPanel() {
  return <textarea aria-label="Notes field" />;
}

const FITTING_TABS: readonly TabDefinition[] = [
  { id: "overview", label: "Overview", content: <OverviewPanel /> },
  { id: "activity", label: "Activity", content: null },
  { id: "details", label: "Details", content: <DetailsPanel /> },
  { id: "notes", label: "Notes", content: <NotesPanel /> },
];

const DISABLED_TABS: readonly TabDefinition[] = [
  ...FITTING_TABS.slice(0, 3),
  { ...FITTING_TABS[3], disabled: true },
];

const OVERFLOW_TABS: readonly TabDefinition[] = [
  ...FITTING_TABS,
  { id: "schedule", label: "Schedule", content: <span aria-hidden="true" /> },
  { id: "insights", label: "Insights", content: <span aria-hidden="true" /> },
  { id: "history", label: "History", content: <span aria-hidden="true" /> },
  { id: "settings", label: "Settings", content: <span aria-hidden="true" /> },
  { id: "sources", label: "Sources", content: <span aria-hidden="true" /> },
  { id: "archive", label: "Archive", content: <span aria-hidden="true" /> },
  { id: "archive-items", label: "Archive items", content: <span aria-hidden="true" /> },
  { id: "analysis", label: "Analysis", content: <span aria-hidden="true" /> },
  { id: "progress", label: "Progress", content: <span aria-hidden="true" /> },
  { id: "bookmarks", label: "Bookmarks", content: <span aria-hidden="true" /> },
  { id: "variations", label: "Variations", content: <span aria-hidden="true" /> },
  { id: "references", label: "References", content: <span aria-hidden="true" /> },
  { id: "history-notes", label: "History notes", content: <span aria-hidden="true" /> },
  { id: "export", label: "Export", content: <span aria-hidden="true" /> },
];

function ControlledTabs() {
  const [selectedId, setSelectedId] = useState("overview");

  return (
    <Tabs
      ariaLabel="Controlled training tabs"
      onSelectedIdChange={setSelectedId}
      selectedId={selectedId}
      tabs={FITTING_TABS}
    />
  );
}

export const Default: Story = {
  name: "Default",
  args: { ariaLabel: "Training tabs", tabs: FITTING_TABS },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const overview = canvas.getByRole("tab", { name: "Overview" });
    const activity = canvas.getByRole("tab", { name: "Activity" });

    await expect(canvas.getByRole("tablist", { name: "Training tabs" })).toBeVisible();
    await expect(overview).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("tabpanel", { name: "Overview" })).toBeVisible();
    await expect(canvas.getByRole("textbox", { name: "Overview field" })).toBeVisible();

    await userEvent.click(activity);
    await expect(activity).toHaveFocus();
    await expect(activity).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("tabpanel", { name: "Activity" })).toBeVisible();
    await expect(canvas.getByTestId("tabs-panel-overview")).toHaveAttribute("hidden");
  },
};

export const Disabled: Story = {
  args: {
    ariaLabel: "Disabled training tabs",
    defaultSelectedId: "overview",
    tabs: DISABLED_TABS,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const overview = canvas.getByRole("tab", { name: "Overview" });
    const notes = canvas.getByRole("tab", { name: "Notes" });

    await expect(notes).toBeDisabled();
    await userEvent.click(notes);
    await expect(overview).toHaveAttribute("aria-selected", "true");

    await overview.focus();
    await userEvent.keyboard("{End}");
    await expect(canvas.getByRole("tab", { name: "Details" })).toHaveFocus();
    await expect(canvas.getByRole("progressbar", { name: "Details progress" })).toBeVisible();
  },
};

export const Controlled: Story = {
  args: { tabs: FITTING_TABS },
  render: () => <ControlledTabs />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const activity = canvas.getByRole("tab", { name: "Activity" });

    await expect(canvas.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await userEvent.click(activity);
    await expect(activity).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("tabpanel", { name: "Activity" })).toBeVisible();
  },
};

export const Overflow: Story = {
  args: { ariaLabel: "Overflow training tabs", tabs: OVERFLOW_TABS },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const previous = canvas.getByRole("button", { name: "Scroll tabs left" });
    const next = canvas.getByRole("button", { name: "Scroll tabs right" });

    await expect(canvas.getByTestId("tabs-navigation")).toHaveAttribute("data-overflow", "true");
    await expect(previous).toBeDisabled();
    await expect(next).toBeEnabled();
    await expect(canvas.getByTestId("tabs-scroll").parentElement).toHaveAttribute(
      "data-hidden-end",
      "true",
    );

    await userEvent.click(next);
    await expect(previous).toBeEnabled();
    await expect(canvas.getByTestId("tabs-scroll").parentElement).toHaveAttribute(
      "data-hidden-start",
      "true",
    );

    const settings = canvas.getByRole("tab", { name: "Settings" });
    await settings.focus();
    await expect(settings).toHaveFocus();
  },
};
