import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const frontendDir = fileURLToPath(new URL(".", import.meta.url));
const backendDir = fileURLToPath(new URL("../backend", import.meta.url));
const webBaseUrl = "http://127.0.0.1:4173";
const apiBaseUrl = "http://127.0.0.1:8000";

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required. Run scripts/e2e.ps1 instead of pnpm test:e2e directly.`);
  }
  return value;
}

// The smoke must never read or write the demo database. Refuse any URL that does
// not point at the isolated verify stack.
const databaseUrl = required("E2E_DATABASE_URL");
if (!databaseUrl.includes(":55434/") || !databaseUrl.includes("scopebridge_verify")) {
  throw new Error(
    "E2E_DATABASE_URL must point at the isolated verify stack (port 55434, database scopebridge_verify).",
  );
}

const backendEnv: Record<string, string> = {
  ...(process.env as Record<string, string>),
  DATABASE_URL: databaseUrl,
  APP_BASE_URL: webBaseUrl,
  SESSION_SECRET: "e2e-only-session-secret-32-characters",
  SELLER_EMAIL: required("E2E_SELLER_EMAIL"),
  SELLER_PASSWORD: required("E2E_SELLER_PASSWORD"),
  CLIENT_EMAIL: required("E2E_CLIENT_EMAIL"),
  CLIENT_PASSWORD: required("E2E_CLIENT_PASSWORD"),
  // Both integrations are intentionally unconfigured: the smoke proves the
  // manual clarification path and the explicit not-configured errors.
  MODEL_API_KEY: "",
  MODEL_NAME: "",
  MODEL_BASE_URL: "",
  PAYPAL_CLIENT_ID: "",
  PAYPAL_CLIENT_SECRET: "",
};

const browserChannel = process.env.E2E_BROWSER_CHANNEL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { outputFolder: "e2e-report", open: "never" }]],
  use: {
    baseURL: webBaseUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // When the bundled Chromium download is unavailable, the wrapper can point
    // the smoke at an installed Chrome or Edge instead.
    channel: browserChannel ? (browserChannel as "chrome" | "msedge") : undefined,
  },
  webServer: [
    {
      command: "uv run uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: backendDir,
      url: `${apiBaseUrl}/api/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: backendEnv,
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 4173 --strictPort",
      cwd: frontendDir,
      url: webBaseUrl,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
