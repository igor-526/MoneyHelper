import { readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import { pwaOptions } from "./src/shared/pwa/pwaOptions.ts";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf-8")) as {
  version: string;
};

// Порт 5173 совпадает с CORS_ORIGINS backend
export default defineConfig({
  plugins: [react(), VitePWA(pwaOptions)],
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
  server: { port: 5173, strictPort: true },
  preview: { port: 5173, strictPort: true },
});
