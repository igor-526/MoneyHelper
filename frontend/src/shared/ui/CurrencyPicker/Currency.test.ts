import { describe, expect, it } from "vitest";
import { type CurrencyDto, mapCurrency } from "./Currency";

describe("mapCurrency", () => {
  it("маппит все поля, включая decimal_places в decimalPlaces", () => {
    const dto: CurrencyDto = { id: "1", code: "USD", name: "Доллар США", decimal_places: 2 };

    expect(mapCurrency(dto)).toEqual({
      id: "1",
      code: "USD",
      name: "Доллар США",
      decimalPlaces: 2,
    });
  });
});
