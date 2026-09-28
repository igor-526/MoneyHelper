import { describe, expect, it } from "vitest";
import { APP_TOKENS, TOUCH_TARGET } from "./tokens";

describe("APP_TOKENS", () => {
  it("высота элементов управления не меньше 44 px", () => {
    expect(APP_TOKENS.controlHeight).toBeGreaterThanOrEqual(44);
    expect(APP_TOKENS.controlHeightLG).toBeGreaterThanOrEqual(44);
    expect(TOUCH_TARGET).toBe(44);
  });

  it("шрифт не меньше 16 px (iOS не увеличивает страницу при фокусе)", () => {
    expect(APP_TOKENS.fontSize).toBeGreaterThanOrEqual(16);
  });
});
