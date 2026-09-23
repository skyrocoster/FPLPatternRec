import "../../../styles/app-tokens.css";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { PageFeedback } from "./PageFeedback";
import styles from "./PageFeedback.module.css";

const meta = {
  title: "Production/Design System/Feedback/Page",
  tags: ["status-production"],
  component: PageFeedback,
  parameters: {
    layout: "fullscreen",
  },
  render: () => (
    <div className={styles.storyGrid}>
      <PageFeedback
        severity="information"
        heading="Information"
        message="This page contains the complete activity summary."
      />
      <PageFeedback
        severity="success"
        heading="Success"
        message="All items on this page match the saved criteria."
      />
      <PageFeedback
        severity="warning"
        heading="Warning"
        message="Several items on this page still need review."
      />
      <PageFeedback
        severity="error"
        heading="Error"
        message="This page contains items that do not match the saved criteria."
      />
    </div>
  ),
} satisfies Meta<typeof PageFeedback>;

export default meta;

type Story = StoryObj<typeof meta>;

export const AllSeverities: Story = {
  args: {
    severity: "information",
    heading: "Information",
    message: "This page contains the complete activity summary.",
  },
};
