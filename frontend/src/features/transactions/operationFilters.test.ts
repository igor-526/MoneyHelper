import dayjs from "dayjs";
import { describe, expect, it } from "vitest";
import { countActiveFilters, EMPTY_OPERATION_FILTERS } from "./operationFilters";

describe("countActiveFilters", () => {
  it("пустые фильтры — 0", () => {
    expect(countActiveFilters(EMPTY_OPERATION_FILTERS)).toBe(0);
  });

  it("считает каждый заданный фильтр", () => {
    expect(
      countActiveFilters({
        walletId: "w1",
        categoryId: undefined,
        dateRange: [dayjs("2026-01-01"), dayjs("2026-01-31")],
      }),
    ).toBe(2);
    expect(countActiveFilters({ walletId: "w1", categoryId: "c1", dateRange: null })).toBe(2);
  });
});
