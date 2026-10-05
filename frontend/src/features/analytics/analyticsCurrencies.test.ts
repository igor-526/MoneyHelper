import { describe, expect, it } from "vitest";
import type { Wallet } from "@/features/wallets/Wallet";
import {
  allowedDisplayCurrencyIds,
  unconvertedMessage,
  walletCurrencyIds,
} from "./analyticsCurrencies";

function wallet(id: string, currencyId: string): Wallet {
  return {
    id,
    name: id,
    icon: "wallet",
    currency_id: currencyId,
    created_at: "",
    updated_at: null,
  };
}

describe("analyticsCurrencies", () => {
  it("walletCurrencyIds: валюты кошельков без повторов", () => {
    expect(walletCurrencyIds([wallet("a", "rub"), wallet("b", "cny"), wallet("c", "rub")])).toEqual(
      ["rub", "cny"],
    );
  });

  it("allowedDisplayCurrencyIds: валюта воркспейса добавляется, если у кошельков её нет", () => {
    expect(allowedDisplayCurrencyIds("rub", [wallet("a", "cny")])).toEqual(["rub", "cny"]);
  });

  it("allowedDisplayCurrencyIds: без повторов, если валюта воркспейса есть у кошелька", () => {
    expect(allowedDisplayCurrencyIds("rub", [wallet("a", "cny"), wallet("b", "rub")])).toEqual([
      "cny",
      "rub",
    ]);
  });

  it("allowedDisplayCurrencyIds: воркспейс ещё не загружен — только валюты кошельков", () => {
    expect(allowedDisplayCurrencyIds(undefined, [wallet("a", "cny")])).toEqual(["cny"]);
  });

  it("unconvertedMessage: коды, причина и подсказка", () => {
    expect(unconvertedMessage(["CNY", "USDT"], "RUB")).toBe(
      "Операции в валютах CNY, USDT не вошли в итоги: за выбранный период нет пополнений, по которым можно вычислить курс к RUB. Выберите другой период или валюту отображения.",
    );
  });
});
