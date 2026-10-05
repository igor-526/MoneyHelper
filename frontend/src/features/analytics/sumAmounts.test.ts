import { describe, expect, it } from "vitest";
import { sumAmounts } from "./sumAmounts";

describe("sumAmounts", () => {
  it("складывает десятичные строки без ошибок float", () => {
    expect(sumAmounts(["0.10", "0.20"])).toBe("0.30");
  });

  it("приводит к максимальному числу знаков", () => {
    expect(sumAmounts(["1", "2.5", "0.125"])).toBe("3.625");
  });

  it("целые суммы остаются целыми", () => {
    expect(sumAmounts(["10", "5"])).toBe("15");
  });

  it("пустой список — ноль", () => {
    expect(sumAmounts([])).toBe("0");
  });

  it("поддерживает большие значения и отрицательные слагаемые", () => {
    expect(sumAmounts(["99999999999999999999.99", "0.01"])).toBe("100000000000000000000.00");
    expect(sumAmounts(["1.00", "-3.50"])).toBe("-2.50");
  });
});
