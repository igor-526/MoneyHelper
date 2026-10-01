import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";

export interface CurrencyRate {
  currency_id: string;
  rate: string;
}

/** Форма ответа backend (`WalletRatesOut`, 021). */
export interface WalletRates {
  target_currency_id: string;
  rates: CurrencyRate[];
  unrated_currency_ids: string[];
}

export function walletRatesQueryKey(
  workspaceId: string,
  walletId: string,
  targetCurrencyId: string,
) {
  return ["wallet-rates", workspaceId, walletId, targetCurrencyId] as const;
}

/**
 * Курс кошелька относительно `targetCurrencyId` (021) — независимый от `useWalletBalances` запрос, тот же
 * приём «сам владеет своим запросом», что и остальные карточки на `TransactionsPage`. `enabled` — тот же приём,
 * что у `useWalletBalances(walletId)`: запрос не выполняется, пока вызывающий не готов (например, кошелёк с
 * одной валютой — курсу не с чем сравниваться).
 */
export function useWalletRates(walletId: string, targetCurrencyId: string, enabled: boolean) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: walletRatesQueryKey(workspaceId, walletId, targetCurrencyId),
    queryFn: ({ signal }) =>
      api.get<WalletRates>(`/api/workspaces/${workspaceId}/wallets/${walletId}/rates`, {
        query: { target_currency_id: targetCurrencyId },
        signal,
      }),
    enabled,
  });
}
