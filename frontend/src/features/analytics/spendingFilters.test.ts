import { describe, expect, it } from "vitest";
import { countSpendingFilters, EMPTY_SPENDING_FILTERS } from "./spendingFilters";

describe("countSpendingFilters", () => {
  it("считает только заданные фильтры", () => {
    expect(countSpendingFilters(EMPTY_SPENDING_FILTERS)).toBe(0);
    expect(countSpendingFilters({ walletId: "w1", categoryId: undefined })).toBe(1);
    expect(countSpendingFilters({ walletId: "w1", categoryId: "c2" })).toBe(2);
  });
});
