import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the page runs on 127.0.0.1:5173 and /api is proxied to the FastAPI app on 127.0.0.1:8000.
// Built: FastAPI serves frontend/dist/ itself, so there is no proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist" },
});
