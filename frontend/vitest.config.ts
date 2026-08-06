import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsxInject: `import React from 'react'`,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    include: [
      "lib/**/*.test.ts",
      // .ts as well as .tsx: helper modules colocated under components/ get
      // logic-only tests, and those were being silently skipped.
      "components/**/__tests__/**/*.test.ts",
      "components/**/__tests__/**/*.test.tsx",
      "components/**/*.test.tsx",
    ],
  },
});
