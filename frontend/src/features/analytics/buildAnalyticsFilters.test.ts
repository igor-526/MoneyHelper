import dayjs from "dayjs";
import { describe, expect, it } from "vitest";
import {
  type AnalyticsPageState,
  INITIAL_ANALYTICS_STATE,
  buildAnalyticsFilters,
} from "./buildAnalyticsFilters";

const DATE_RANGE: [ReturnType<typeof dayjs>, ReturnType<typeof dayjs>] = [
  dayjs("2026-03-01"),
  dayjs("2026-03-10"),
];

const FULL_STATE: AnalyticsPageState = {
  ...INITIAL_ANALYTICS_STATE,
  displayCurrencyId: "cur1",
  dateRange: DATE_RANGE,
  groupBy: "wallet",
};

describe("buildAnalyticsFilters", () => {
  it("null, если не заполнена валюта отображения", () => {
    expect(buildAnalyticsFilters({ ...FULL_STATE, displayCurrencyId: undefined })).toBeNull();
  });

  it("null, если не заполнен диапазон дат", () => {
    expect(buildAnalyticsFilters({ ...FULL_STATE, dateRange: null })).toBeNull();
  });

  it("null, если не заполнен срез", () => {
    expect(buildAnalyticsFilters({ ...FULL_STATE, groupBy: undefined })).toBeNull();
  });

  it("null, если не заполнены два из трёх обязательных полей", () => {
    expect(
      buildAnalyticsFilters({ ...FULL_STATE, displayCurrencyId: undefined, groupBy: undefined }),
    ).toBeNull();
    expect(
      buildAnalyticsFilters({ ...FULL_STATE, dateRange: null, groupBy: undefined }),
    ).toBeNull();
    expect(
      buildAnalyticsFilters({ ...FULL_STATE, displayCurrencyId: undefined, dateRange: null }),
    ).toBeNull();
  });

  it("null, если не заполнено ни одно обязательное поле (начальное состояние)", () => {
    expect(buildAnalyticsFilters(INITIAL_ANALYTICS_STATE)).toBeNull();
  });

  it("заполнены все обязательные поля без сужающих фильтров: корректный результат", () => {
    expect(buildAnalyticsFilters(FULL_STATE)).toEqual({
      displayCurrencyId: "cur1",
      dateFrom: DATE_RANGE[0].startOf("day").toISOString(),
      dateTo: DATE_RANGE[1].endOf("day").toISOString(),
      groupBy: "wallet",
      walletId: undefined,
      categoryId: undefined,
      currencyId: undefined,
      type: undefined,
    });
  });

  it("dateFrom/dateTo — начало первого и конец последнего выбранного дня", () => {
    const result = buildAnalyticsFilters(FULL_STATE);
    expect(result?.dateFrom).toBe(DATE_RANGE[0].startOf("day").toISOString());
    expect(result?.dateTo).toBe(DATE_RANGE[1].endOf("day").toISOString());
  });

  it("каждый сужающий фильтр по отдельности передаётся в результат", () => {
    expect(buildAnalyticsFilters({ ...FULL_STATE, walletId: "w1" })).toMatchObject({
      walletId: "w1",
    });
    expect(buildAnalyticsFilters({ ...FULL_STATE, categoryId: "c1" })).toMatchObject({
      categoryId: "c1",
    });
    expect(buildAnalyticsFilters({ ...FULL_STATE, currencyId: "cur2" })).toMatchObject({
      currencyId: "cur2",
    });
    expect(buildAnalyticsFilters({ ...FULL_STATE, type: "income" })).toMatchObject({
      type: "income",
    });
  });

  it("комбинация сужающих фильтров передаётся одновременно", () => {
    expect(
      buildAnalyticsFilters({
        ...FULL_STATE,
        walletId: "w1",
        categoryId: "c1",
        currencyId: "cur2",
        type: "expense",
      }),
    ).toMatchObject({
      walletId: "w1",
      categoryId: "c1",
      currencyId: "cur2",
      type: "expense",
    });
  });

  it('type: "all" даёт type: undefined в результате', () => {
    expect(buildAnalyticsFilters({ ...FULL_STATE, type: "all" })).toMatchObject({
      type: undefined,
    });
  });
});
