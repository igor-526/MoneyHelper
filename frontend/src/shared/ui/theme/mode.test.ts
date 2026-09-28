import { describe, expect, it } from "vitest";
import { parseThemeMode, resolveTheme } from "./mode";

describe("resolveTheme", () => {
  it.each([
    ["system", true, "dark"],
    ["system", false, "light"],
    ["dark", false, "dark"],
    ["light", true, "light"],
  ] as const)("режим %s, системная тёмная=%s -> %s", (mode, systemDark, expected) => {
    expect(resolveTheme(mode, systemDark)).toBe(expected);
  });
});

describe("parseThemeMode", () => {
  it.each(["light", "dark", "system"])("принимает %s", (value) => {
    expect(parseThemeMode(value)).toBe(value);
  });

  it.each(["blue", "", null, undefined, 1])("некорректное значение %j -> system", (value) => {
    expect(parseThemeMode(value)).toBe("system");
  });
});
