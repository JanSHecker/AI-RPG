import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:8000',
    headless: true,
  },
  webServer: {
    command:
      "sh -lc 'rm -f ../.playwright-ai-rpg.db && npm run build && AI_RPG_DB_PATH=../.playwright-ai-rpg.db node ../scripts/backend.mjs dev'",
    port: 8000,
    reuseExistingServer: true,
    cwd: '.',
    timeout: 120_000,
  },
})
