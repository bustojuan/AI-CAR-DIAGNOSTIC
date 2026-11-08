import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": process.env.API_PROXY_TARGET || "http://127.0.0.1:8002" },
  },
  preview: { port: 4173, strictPort: true },
  test: {
    // Fresh thread workers intermittently stall during startup on this Windows
    // workspace. Process isolation retains per-file isolation and is verified here.
    pool: process.platform === "win32" ? "forks" : "threads",
    maxWorkers: 1,
    testTimeout: process.platform === "win32" ? 15000 : 5000,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
