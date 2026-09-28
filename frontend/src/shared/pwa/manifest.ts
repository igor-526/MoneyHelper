import type { ManifestOptions } from "vite-plugin-pwa";

export const BRAND_COLOR = "#1677ff";

/** Единый источник manifest: используется плагином PWA и тестами. */
export const manifest: Partial<ManifestOptions> = {
  name: "MoneyHelper",
  short_name: "MoneyHelper",
  description: "Личный учёт финансов: кошельки, доходы, расходы и аналитика",
  lang: "ru",
  start_url: "/",
  scope: "/",
  display: "standalone",
  theme_color: BRAND_COLOR,
  background_color: "#ffffff",
  icons: [
    { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
    { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
    { src: "pwa-512x512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    { src: "maskable-icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
  ],
};
