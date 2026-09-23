import type { Meta, StoryObj } from "@storybook/react-vite";
import "../../styles/app-tokens.css";
import "../../styles/app-typescale.css";
import { Button, type ButtonSize, type ButtonVariant } from "./Button";

const meta = {
  title: "Production/Design System/Components/Button",
  tags: ["status-production"],
  component: Button,
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

const VARIANTS: ButtonVariant[] = ["primary", "secondary", "ghost"];
const SIZES: ButtonSize[] = ["md", "sm"];

const shell = (children: React.ReactNode) => (
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
    {children}
  </main>
);

export const VariantMatrix: Story = {
  render: () =>
    shell(
      <>
        <h1 style={{ margin: "0 0 var(--app-spacing-8)", fontSize: "20px" }}>Button</h1>
        <p
          style={{
            margin: "0 0 var(--app-spacing-16)",
            fontSize: "13px",
            color: "var(--md-sys-color-on-surface-variant)",
          }}
        >
          The three token-driven variants across the two sizes, plus the disabled state. Built on
          the Base UI headless Button primitive.
        </p>

        {SIZES.map((size) => (
          <section key={size}>
            <h2
              style={{
                margin: "0 0 var(--app-spacing-8)",
                fontSize: "14px",
                textTransform: "capitalize",
              }}
            >
              {size}
            </h2>
            <div style={{ display: "flex", gap: "var(--app-spacing-12)", flexWrap: "wrap" }}>
              {VARIANTS.map((variant) => (
                <Button key={variant} variant={variant} size={size}>
                  {variant}
                </Button>
              ))}
              {VARIANTS.map((variant) => (
                <Button key={`${variant}-disabled`} variant={variant} size={size} disabled>
                  {variant}
                </Button>
              ))}
            </div>
          </section>
        ))}
      </>,
    ),
};
