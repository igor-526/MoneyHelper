import type { QueryClient } from "@tanstack/react-query";
import { transfersQueryKey } from "./useTransfers";

/**
 * Локальная копия ключа кэша балансов — НЕ импорт `walletBalancesQueryKey` из `features/transactions`.
 * TanStack Query сравнивает `queryKey` структурно, поэтому локальный `["wallet-balances", workspaceId]`
 * достигает того же эффекта без кросс-фичевого импорта (`transactions` уже зависит от `transfers`).
 */
function walletBalancesQueryKey(workspaceId: string) {
  return ["wallet-balances", workspaceId] as const;
}

/** Перевод меняет только списки переводов и балансы; курсы и аналитика от него не зависят. */
export function invalidateTransferCaches(queryClient: QueryClient, workspaceId: string) {
  for (const queryKey of [transfersQueryKey(workspaceId), walletBalancesQueryKey(workspaceId)]) {
    queryClient.invalidateQueries({ queryKey });
  }
}
