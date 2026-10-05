import type { Wallet } from "@/features/wallets/Wallet";

/** Валюты кошельков воркспейса без повторов — валюты, в которых бывают операции. */
export function walletCurrencyIds(wallets: Wallet[]): string[] {
  return [...new Set(wallets.map((wallet) => wallet.currency_id))];
}

/** Допустимые валюты отображения (029): валюта воркспейса и валюты его кошельков. */
export function allowedDisplayCurrencyIds(
  workspaceCurrencyId: string | undefined,
  wallets: Wallet[],
): string[] {
  const ids = walletCurrencyIds(wallets);
  if (workspaceCurrencyId === undefined || ids.includes(workspaceCurrencyId)) return ids;
  return [workspaceCurrencyId, ...ids];
}

export function unconvertedMessage(unconvertedCodes: string[], displayCode: string): string {
  return `Операции в валютах ${unconvertedCodes.join(", ")} не вошли в итоги: за выбранный период нет пополнений, по которым можно вычислить курс к ${displayCode}. Выберите другой период или валюту отображения.`;
}
