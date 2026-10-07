import { describe, expect, it } from "vitest";
import type { Wallet } from "@/features/wallets/Wallet";
import type { Currency } from "@/shared/ui";
import { rateCurrencies } from "./rateCurrencies";

const currencies: Currency[] = [
  { id: "rub", code: "RUB", name: "Рубль", decimalPlaces: 2 },
  { id: "usdt", code: "USDT", name: "Tether", decimalPlaces: 8 },
  { id: "cny", code: "CNY", name: "Юань", decimalPlaces: 2 },
  { id: "usd", code: "USD", name: "Доллар", decimalPlaces: 2 },
];

function wallet(currencyId: string): Wallet {
  return {
    id: `wallet-${currencyId}`,
    name: currencyId,
    icon: "wallet",
    currency_id: currencyId,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  };
}

describe("rateCurrencies", () => {
  it("объединяет валюту воркспейса и кошельков, исключает RUB и сортирует", () => {
    expect(
      rateCurrencies(
        "usd",
        [wallet("rub"), wallet("usdt"), wallet("cny"), wallet("cny")],
        currencies,
      ),
    ).toEqual([currencies[2], currencies[3], currencies[1]]);
  });

  it("возвращает пустой список для только рублёвого воркспейса", () => {
    expect(rateCurrencies("rub", [wallet("rub")], currencies)).toEqual([]);
  });
});
