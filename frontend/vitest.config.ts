import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    // Default for the data-layer tests. Component tests opt into jsdom with a
    // `// @vitest-environment jsdom` docblock, so only the files that need a DOM
    // pay for one.
    environment: 'node',
    globals: true,
    setupFiles: [],
  },
  // tsconfig.json uses "jsx": "preserve" for Next's own compiler, which leaves
  // esbuild on the classic transform — every .tsx test would need React in
  // scope. React 18's automatic runtime is what the app is built with.
  esbuild: {
    jsx: 'automatic',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
})
