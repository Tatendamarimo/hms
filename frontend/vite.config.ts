/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
    globals: true,
  },
  server: {
    port: 5173,
    proxy: {
      // Same-origin in dev: session cookie + CSRF just work
      "/api": "http://localhost:8000",
      "/print": "http://localhost:8000",
    },
  },
});
