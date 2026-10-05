import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { WalletBalance } from "./Transaction";

export function walletBalancesQueryKey(workspaceId: string) {
  return ["wallet-balances", workspaceId] as const;
}

/** `enabled: false` при отсутствующем `walletId` — карточка баланса не показывается при фильтре «Все кошельки». */
export function useWalletBalances(walletId: string | undefined) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: [...walletBalancesQueryKey(workspaceId), walletId],
    queryFn: ({ signal }) =>
      api.get<WalletBalance>(`/api/workspaces/${workspaceId}/wallets/${walletId}/balances`, {
        signal,
      }),
    enabled: walletId !== undefined,
  });
}
