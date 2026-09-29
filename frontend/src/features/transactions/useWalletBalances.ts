import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { WalletBalance } from "./Transaction";

export const WALLET_BALANCES_QUERY_KEY = ["wallet-balances"] as const;

/** `enabled: false` при отсутствующем `walletId` — карточка баланса не показывается при фильтре «Все кошельки». */
export function useWalletBalances(walletId: string | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: [...WALLET_BALANCES_QUERY_KEY, walletId],
    queryFn: ({ signal }) =>
      api.get<WalletBalance[]>(`/api/wallets/${walletId}/balances`, { signal }),
    enabled: walletId !== undefined,
  });
}
