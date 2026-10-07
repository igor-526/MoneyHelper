import type { MockInstance } from "vitest";
import { expect } from "vitest";
import { analyticsQueryKey } from "@/features/analytics/useAnalytics";
import { topupsQueryKey } from "@/features/transactions/useTopups";
import { transactionsQueryKey } from "@/features/transactions/useTransactions";
import { walletRatesQueryKey } from "@/features/wallets/useWalletRates";

/** Проверяет, что после операции инвалидированы списки, курсы и аналитика воркспейса. */
export function expectOperationCachesInvalidated(spy: MockInstance, workspaceId: string) {
  for (const queryKey of [
    transactionsQueryKey(workspaceId),
    topupsQueryKey(workspaceId),
    walletRatesQueryKey(workspaceId),
    analyticsQueryKey(workspaceId),
  ]) {
    expect(spy).toHaveBeenCalledWith({ queryKey });
  }
}
