import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { AnalyticsFilters, AnalyticsResult } from "./Analytics";

export const ANALYTICS_QUERY_KEY = ["analytics"] as const;

/** `enabled: filters !== null` — то же обобщение паттерна `useWalletBalances(walletId)` (016) на составной вход:
 *  запрос не выполняется, пока не заполнены все обязательные поля. */
export function useAnalytics(filters: AnalyticsFilters | null) {
  const api = useApiClient();
  return useQuery({
    queryKey: [...ANALYTICS_QUERY_KEY, filters],
    queryFn: ({ signal }) =>
      // Ненулевое утверждение `filters!` безопасно: `enabled` ниже гарантирует, что TanStack Query никогда не
      // вызовет `queryFn` при `filters === null`.
      api.get<AnalyticsResult>("/api/analytics", {
        query: {
          display_currency: filters!.displayCurrencyId,
          date_from: filters!.dateFrom,
          date_to: filters!.dateTo,
          group_by: filters!.groupBy,
          wallet_id: filters!.walletId,
          category_id: filters!.categoryId,
          currency_id: filters!.currencyId,
          type: filters!.type,
        },
        signal,
      }),
    enabled: filters !== null,
  });
}
