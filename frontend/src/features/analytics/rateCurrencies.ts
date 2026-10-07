import type { Wallet } from "@/features/wallets/Wallet";
import type { Currency } from "@/shared/ui";

export function rateCurrencies(
  workspaceCurrencyId: string | undefined,
  wallets: Wallet[],
  currencies: Currency[],
): Currency[] {
  const allowedIds = new Set(wallets.map((wallet) => wallet.currency_id));
  if (workspaceCurrencyId !== undefined) allowedIds.add(workspaceCurrencyId);
  return currencies
    .filter((currency) => allowedIds.has(currency.id) && currency.code !== "RUB")
    .sort((left, right) => left.code.localeCompare(right.code));
}
