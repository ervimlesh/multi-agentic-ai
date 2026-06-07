import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Forward API calls to the FastAPI backend during development.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
      // Forward agent runs to the agent-engine (LangGraph + Groq) service.
      "/agent": { target: "http://localhost:8100", changeOrigin: true },
    },
  },
});
