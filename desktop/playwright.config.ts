import { defineConfig } from "@playwright/test";

const baseURL = "http://127.0.0.1:6006";

export default defineConfig({
  testDir: "./tests",
  use: { baseURL, browserName: "chromium" },
  webServer: {
    command: "npm run storybook -- --ci --host 127.0.0.1",
    url: baseURL,
    timeout: 60_000,
    reuseExistingServer: !process.env.CI,
  },
});
