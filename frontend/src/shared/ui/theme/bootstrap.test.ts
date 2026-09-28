import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { setMedia } from "@/test/matchMedia";
import { DARK_QUERY } from "./ThemeProvider";
import { resolveTheme, type ThemeMode } from "./mode";

const html = readFileSync(resolve(process.cwd(), "index.html"), "utf-8");
const script = /<script id="theme-bootstrap">([\s\S]*?)<\/script>/.exec(html)?.[1] ?? "";

function runBootstrap(stored: string | null, systemDark: boolean): string | null {
  document.documentElement.removeAttribute("data-theme");
  window.localStorage.clear();
  if (stored !== null) window.localStorage.setItem("moneyhelper.theme", stored);
  setMedia(DARK_QUERY, systemDark);
  new Function(script)();
  return document.documentElement.getAttribute("data-theme");
}

describe("встроенный скрипт темы (index.html)", () => {
  beforeEach(() => expect(script).not.toBe(""));

  it.each([
    ["light", false],
    ["light", true],
    ["dark", false],
    ["dark", true],
    ["system", false],
    ["system", true],
    [null, true],
    [null, false],
    ["blue", true],
  ] as const)(
    "совпадает с resolveTheme: сохранено=%s, системная тёмная=%s",
    (stored, systemDark) => {
      const mode: ThemeMode = stored === "light" || stored === "dark" ? stored : "system";
      expect(runBootstrap(stored, systemDark)).toBe(resolveTheme(mode, systemDark));
    },
  );
});
