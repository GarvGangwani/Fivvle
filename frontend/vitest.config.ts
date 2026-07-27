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
      "components/**/__tests__/**/*.test.tsx",
      "components/**/*.test.tsx",
    ],
  },
});
