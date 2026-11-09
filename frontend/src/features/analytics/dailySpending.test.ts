import { describe, expect, it } from "vitest";
import { buildDailySpending, spendingChartSeries, totalSpending } from "./dailySpending";

const bucket = (day: string, expense: string) => ({ group_key: day, income: "0", expense });

describe("buildDailySpending", () => {
  it("без диапазона идёт от первого до последнего дня с тратами и заполняет пропуски нулями", () => {
    const series = buildDailySpending(
      [bucket("2026-01-03", "30"), bucket("2026-01-01", "10.50")],
      {},
    );

    expect(series).toEqual([
      { day: "2026-01-01", amount: "10.50" },
      { day: "2026-01-02", amount: "0" },
      { day: "2026-01-03", amount: "30" },
    ]);
  });

  it("с диапазоном показывает все его дни, включая пустые", () => {
    const series = buildDailySpending([bucket("2026-01-02", "5")], {
      dateFrom: new Date(2026, 0, 1).toISOString(),
      dateTo: new Date(2026, 0, 3, 23, 59, 59).toISOString(),
    });

    expect(series.map((point) => point.day)).toEqual(["2026-01-01", "2026-01-02", "2026-01-03"]);
    expect(series.map((point) => point.amount)).toEqual(["0", "5", "0"]);
  });

  it("без трат и без диапазона возвращает пустой ряд", () => {
    expect(buildDailySpending([], {})).toEqual([]);
  });
});

describe("totalSpending", () => {
  it("точно суммирует дни", () => {
    expect(
      totalSpending([
        { day: "2026-01-01", amount: "0.10" },
        { day: "2026-01-02", amount: "0.20" },
      ]),
    ).toBe("0.30");
  });
});

describe("spendingChartSeries", () => {
  it("сохраняет только даты операций и не меняет статистику полного диапазона", () => {
    const buckets = [bucket("2026-01-03", "30.00"), bucket("2026-01-01", "10.00")];
    expect(spendingChartSeries(buckets)).toEqual([
      { day: "2026-01-01", amount: "10.00" },
      { day: "2026-01-03", amount: "30.00" },
    ]);
    expect(buildDailySpending(buckets, {}).map((point) => point.amount)).toEqual([
      "10.00",
      "0",
      "30.00",
    ]);
  });
  it("не удаляет дату с нулевым итогом", () => {
    expect(spendingChartSeries([bucket("2026-01-01", "0")])).toEqual([
      { day: "2026-01-01", amount: "0" },
    ]);
  });
});
