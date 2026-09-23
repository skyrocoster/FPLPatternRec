import "../../../styles/app-tokens.css";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { PanelFeedback } from "./PanelFeedback";
import styles from "./PanelFeedback.module.css";

const meta = {
  title: "Production/Design System/Feedback/Panel",
  tags: ["status-production"],
  component: PanelFeedback,
  parameters: {
    layout: "fullscreen",
  },
  render: () => (
    <div className={styles.storyGrid}>
      <PanelFeedback
        severity="information"
        heading="Information"
        message="The saved item is ready for review."
      />
      <PanelFeedback
        severity="success"
        heading="Success"
        message="The selected option matches the saved criteria."
      />
      <PanelFeedback
        severity="warning"
        heading="Warning"
        message="This change may affect related records."
      />
      <PanelFeedback
        severity="error"
        heading="Error"
        message="The submitted value is not valid for this record."
      />
    </div>
  ),
} satisfies Meta<typeof PanelFeedback>;

export default meta;

type Story = StoryObj<typeof meta>;

export const AllSeverities: Story = {
  args: {
    severity: "information",
    heading: "Information",
    message: "The saved item is ready for review.",
  },
};
