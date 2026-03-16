import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: './vitest.setup.ts',
    include: ['src/__tests__/**/*.test.ts?(x)'],
    exclude: ['tests/e2e/**'],
  },
})
