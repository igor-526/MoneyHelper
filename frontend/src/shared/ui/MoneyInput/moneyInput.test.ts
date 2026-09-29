import { describe, expect, it } from "vitest";
import { isValidMoneyAmount } from "./moneyInput";

describe("isValidMoneyAmount", () => {
  it("допускает цифры и точку", () => {
    expect(isValidMoneyAmount("123")).toBe(true);
    expect(isValidMoneyAmount("123.45")).toBe(true);
    expect(isValidMoneyAmount("")).toBe(true);
  });

  it("отклоняет недопустимый символ", () => {
    expect(isValidMoneyAmount("12a")).toBe(false);
    expect(isValidMoneyAmount("-1")).toBe(false);
    expect(isValidMoneyAmount("1,5")).toBe(false);
  });

  it("отклоняет более одной точки", () => {
    expect(isValidMoneyAmount("1.2.3")).toBe(false);
    expect(isValidMoneyAmount("1..2")).toBe(false);
  });

  it("допускает промежуточное состояние ввода без цифр после точки", () => {
    expect(isValidMoneyAmount("12.")).toBe(true);
    expect(isValidMoneyAmount(".")).toBe(true);
  });

  it("ограничивает число знаков после точки при заданном decimalPlaces", () => {
    expect(isValidMoneyAmount("12.34", 2)).toBe(true);
    expect(isValidMoneyAmount("12.345", 2)).toBe(false);
    expect(isValidMoneyAmount("12.", 2)).toBe(true);
    expect(isValidMoneyAmount("12", 0)).toBe(true);
    expect(isValidMoneyAmount("12.5", 0)).toBe(false);
  });

  it("без decimalPlaces ограничения на число знаков нет", () => {
    expect(isValidMoneyAmount("12.12345678901234")).toBe(true);
  });
});
