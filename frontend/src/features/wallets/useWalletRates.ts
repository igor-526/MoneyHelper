import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";

/** Форма ответа backend (`WalletRateOut`, 029): `rate` — `null`, если пополнений с обеими ногами ещё нет. */
export interface WalletRate {
  workspace_currency_id: string;
  wallet_currency_id: string;
  rate: string | null;
}

/** Без `walletId` — префикс всех курсов воркспейса (для инвалидации). */
export function walletRatesQueryKey(workspaceId: string, walletId?: string) {
  return walletId === undefined
    ? (["wallet-rates", workspaceId] as const)
    : (["wallet-rates", workspaceId, walletId] as const);
}

/** Курс кошелька к валюте воркспейса (029) — независимый от `useWalletBalances` запрос. */
export function useWalletRates(walletId: string) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: walletRatesQueryKey(workspaceId, walletId),
    queryFn: ({ signal }) =>
      api.get<WalletRate>(`/api/workspaces/${workspaceId}/wallets/${walletId}/rates`, { signal }),
  });
}
