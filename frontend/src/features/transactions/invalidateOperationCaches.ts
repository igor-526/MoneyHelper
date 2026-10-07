import type { QueryClient } from "@tanstack/react-query";
import { analyticsQueryKey } from "@/features/analytics/useAnalytics";
import { walletRatesQueryKey } from "@/features/wallets/useWalletRates";
import { topupsQueryKey } from "./useTopups";
import { transactionsQueryKey } from "./useTransactions";

/** Всё, что зависит от пополнений и расходов: списки, курсы кошельков и аналитика воркспейса. */
export function invalidateOperationCaches(queryClient: QueryClient, workspaceId: string) {
  for (const queryKey of [
    transactionsQueryKey(workspaceId),
    topupsQueryKey(workspaceId),
    walletRatesQueryKey(workspaceId),
    analyticsQueryKey(workspaceId),
  ]) {
    queryClient.invalidateQueries({ queryKey });
  }
}
