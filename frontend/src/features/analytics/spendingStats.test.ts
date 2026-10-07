import { describe, expect, it } from "vitest";
import { spendingStats } from "./spendingStats";

describe("spendingStats", () => {
  it("учитывает нулевые дни", () => {
    expect(
      spendingStats([
        { day: "2026-01-01", amount: "10.00" },
        { day: "2026-01-02", amount: "0" },
        { day: "2026-01-03", amount: "20.00" },
      ]),
    ).toEqual([
      { label: "Минимум", value: "0.00" },
      { label: "Максимум", value: "20.00" },
      { label: "Средняя", value: "10.00" },
      { label: "Медиана", value: "10.00" },
    ]);
  });

  it("считает медиану чётного ряда без float", () => {
    const result = spendingStats(
      ["0.00", "10.00", "20.00", "30.00"].map((amount, index) => ({ day: String(index), amount })),
    );
    expect(result.find((item) => item.label === "Медиана")?.value).toBe("15.00");
  });

  it("округляет среднее до масштаба исходной валюты", () => {
    const result = spendingStats(
      ["0.01", "0.02", "0.02"].map((amount, index) => ({ day: String(index), amount })),
    );
    expect(result.find((item) => item.label === "Средняя")?.value).toBe("0.02");
  });

  it("для пустой серии возвращает пустой список", () => {
    expect(spendingStats([])).toEqual([]);
  });
});
