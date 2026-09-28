import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { manifest } from "./manifest";
import { pwaOptions } from "./pwaOptions";

const publicDir = resolve(process.cwd(), "public");
const indexHtml = readFileSync(resolve(process.cwd(), "index.html"), "utf-8");

describe("manifest", () => {
  it("содержит обязательные поля", () => {
    expect(manifest).toMatchObject({
      name: "MoneyHelper",
      lang: "ru",
      start_url: "/",
      scope: "/",
      display: "standalone",
    });
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.description).toBeTruthy();
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i);
    expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("содержит иконки 192, 512 и maskable 512", () => {
    const icons = manifest.icons ?? [];
    const has = (sizes: string, purpose?: string) =>
      icons.some((icon) => icon.sizes === sizes && icon.purpose === purpose);
    expect(has("192x192")).toBe(true);
    expect(has("512x512", "any")).toBe(true);
    expect(has("512x512", "maskable")).toBe(true);
  });

  it("файлы иконок существуют в public/", () => {
    for (const icon of manifest.icons ?? []) {
      expect(existsSync(resolve(publicDir, icon.src)), icon.src).toBe(true);
    }
    expect(existsSync(resolve(publicDir, "apple-touch-icon-180x180.png"))).toBe(true);
    expect(existsSync(resolve(publicDir, "favicon.ico"))).toBe(true);
  });
});

describe("index.html", () => {
  it.each([
    'name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"',
    'name="apple-mobile-web-app-capable"',
    'name="apple-mobile-web-app-title"',
    'name="apple-mobile-web-app-status-bar-style"',
    'rel="apple-touch-icon"',
  ])("содержит %s", (fragment) => {
    expect(indexHtml).toContain(fragment);
  });
});

describe("service worker", () => {
  it("обновление только по подтверждению пользователя", () => {
    expect(pwaOptions.registerType).toBe("prompt");
  });

  it("кэширует оболочку и отдаёт index.html для навигации SPA", () => {
    expect(pwaOptions.workbox?.navigateFallback).toBe("/index.html");
    expect(pwaOptions.workbox?.cleanupOutdatedCaches).toBe(true);
    expect(pwaOptions.workbox?.globPatterns).toEqual(
      expect.arrayContaining([expect.stringContaining("html"), expect.stringContaining("js")]),
    );
  });

  it("не кэширует запросы к API (нет runtimeCaching)", () => {
    expect(pwaOptions.workbox?.runtimeCaching).toBeUndefined();
    expect(JSON.stringify(pwaOptions)).not.toContain("VITE_API_URL");
  });

  it("выключен в dev-сервере", () => {
    expect(pwaOptions.devOptions?.enabled).toBe(false);
  });
});
