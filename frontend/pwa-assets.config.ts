import { defineConfig, minimal2023Preset as preset } from "@vite-pwa/assets-generator/config";

const BRAND = "#1677ff";

export default defineConfig({
  preset: {
    ...preset,
    maskable: { ...preset.maskable, resizeOptions: { background: BRAND } },
    apple: { ...preset.apple, resizeOptions: { background: BRAND } },
  },
  images: ["public/icon.svg"],
});
