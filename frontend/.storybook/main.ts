import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/features/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-vitest"],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  viteFinal: (config) => {
    // The static Storybook build bundles the monolithic axe-core engine
    // (@storybook/addon-a11y) and the preview iframe runtime, which exceed
    // Vite's default 500 kB chunk-size advisory. These are Storybook tooling
    // chunks, not application code; the app build stays code-split and below
    // the default limit.
    config.build ??= {};
    config.build.chunkSizeWarningLimit = 1600;
    return config;
  },
};

export default config;
