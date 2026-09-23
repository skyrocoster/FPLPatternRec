import type { Meta, StoryObj } from "@storybook/react-vite";
import "../../../styles/app-tokens.css";
import { FeedbackCore } from "./FeedbackCore";
import { FEEDBACK_VARIANTS } from "./feedbackTypes";
import type { FeedbackSeverity } from "./feedbackTypes";

const meta = {
  title: "Reference/Design System/Feedback Semantic Variants",
  tags: ["status-reference"],
  component: FeedbackCore,
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof FeedbackCore>;

export default meta;

type Story = StoryObj<typeof meta>;

const SEVERITIES: FeedbackSeverity[] = ["information", "success", "warning", "error"];

const MESSAGES: Record<FeedbackSeverity, string> = {
  information: "The position was loaded and is ready for review.",
  success: "The update was recorded and the item was refreshed.",
  warning: "The submitted record is missing a required value.",
  error: "The change could not be applied to the current item.",
};

export const SemanticVariants: Story = {
  args: {
    severity: "information",
    message: "The position was loaded and is ready for review.",
  },
  render: () => (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--app-spacing-24)",
        padding: "var(--app-spacing-24)",
        minHeight: "100vh",
        backgroundColor: "var(--md-sys-color-surface)",
        color: "var(--md-sys-color-on-surface)",
        fontFamily: "system-ui",
      }}
    >
      {SEVERITIES.map((severity) => {
        const tokens = FEEDBACK_VARIANTS[severity].tokens;
        return (
          <section key={severity}>
            <h2
              style={{
                margin: "0 0 var(--app-spacing-8)",
                fontSize: "16px",
                textTransform: "capitalize",
              }}
            >
              {severity}
            </h2>
            <p
              style={{
                margin: "0 0 var(--app-spacing-8)",
                fontSize: "13px",
                color: "var(--md-sys-color-on-surface-variant)",
              }}
            >
              {tokens.accent} / {tokens.onAccent} / {tokens.container} / {tokens.onContainer}
            </p>
            <FeedbackCore
              severity={severity}
              heading={severity === "information" ? "Heads up" : undefined}
              message={MESSAGES[severity]}
            />
          </section>
        );
      })}
    </main>
  ),
};
