import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev proxy: the SPA talks to the ExoDossier FastAPI service on :8700 under /api.
// In mock mode (VITE_API_MOCK=1) the client never hits the network — fixtures are served from
// src/api/fixtures — so this proxy is inert and the catalog is fully explorable before the API is up.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8700",
        changeOrigin: true,
      },
    },
  },
});
