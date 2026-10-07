import { describe, expect, it } from "vitest";
import { rateStats } from "./rateStats";

describe("rateStats", () => {
  it("считает минимум, максимум и среднее по дневным точкам", () => {
    expect(
      rateStats([
        { date: "2026-01-01", rate: "10.0000000000" },
        { date: "2026-01-02", rate: "14.0000000000" },
        { date: "2026-01-03", rate: "12.0000000000" },
      ]),
    ).toEqual([
      { label: "Минимум", value: "10.0000000000" },
      { label: "Максимум", value: "14.0000000000" },
      { label: "Средняя", value: "12.0000000000" },
    ]);
  });

  it("возвращает одинаковые агрегаты для одной точки", () => {
    expect(rateStats([{ date: "2026-01-01", rate: "13.2500000000" }])).toEqual([
      { label: "Минимум", value: "13.2500000000" },
      { label: "Максимум", value: "13.2500000000" },
      { label: "Средняя", value: "13.2500000000" },
    ]);
  });

  it("возвращает пустой список без точек", () => {
    expect(rateStats([])).toEqual([]);
  });
});
