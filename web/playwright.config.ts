import { defineConfig, devices } from "@playwright/test";

// With E2E_EMAIL/E2E_PASSWORD the panel runs against the real Supabase project;
// otherwise the Supabase variables are blank and only "sem sessão" tests run.
const authenticated = Boolean(process.env.E2E_EMAIL && process.env.E2E_PASSWORD);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: process.env.CI ? "list" : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "mobile",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: {
    command: "./node_modules/.bin/next dev",
    env: {
      NEXT_PUBLIC_SUPABASE_URL: authenticated ? (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "") : "",
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: authenticated ? (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "") : "",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: authenticated ? (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "") : "",
    },
    url: "http://127.0.0.1:3000/login",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
