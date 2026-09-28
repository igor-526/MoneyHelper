import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: false,
      include: ["src/**/*.test.{ts,tsx}"],
      alias: {
        "virtual:pwa-register/react": new URL("./src/test/pwa-register-react.ts", import.meta.url)
          .pathname,
      },
    },
  }),
);
