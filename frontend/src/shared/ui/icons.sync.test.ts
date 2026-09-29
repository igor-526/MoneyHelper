import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { BUSINESS_ICON_NAMES } from "./icons";

describe("реестр иконок синхронизирован с backend", () => {
  it("BUSINESS_ICON_NAMES совпадает с backend/src/core/icons.json", () => {
    const raw = readFileSync(resolve(process.cwd(), "../backend/src/core/icons.json"), "utf-8");
    const backendIcons: string[] = JSON.parse(raw);
    expect(new Set(BUSINESS_ICON_NAMES)).toEqual(new Set(backendIcons));
  });
});
