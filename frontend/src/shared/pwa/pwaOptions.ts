import type { VitePWAOptions } from "vite-plugin-pwa";
import { manifest } from "./manifest.ts";

/**
 * Настройки service worker. Кэшируется только оболочка приложения (precache).
 * Runtime-кэширования нет намеренно: запросы к API идут напрямую в сеть, чтобы не показывать
 * устаревшие финансовые данные и не хранить ответы с данными пользователя.
 */
export const pwaOptions: Partial<VitePWAOptions> = {
  registerType: "prompt",
  strategies: "generateSW",
  includeAssets: ["favicon.ico", "apple-touch-icon-180x180.png", "icon.svg"],
  manifest,
  workbox: {
    globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
    navigateFallback: "/index.html",
    cleanupOutdatedCaches: true,
  },
  devOptions: { enabled: false },
};
