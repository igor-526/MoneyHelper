import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { AnalyticsRange, ExchangeRateHistory } from "./Analytics";

export function exchangeRateHistoryQueryKey(workspaceId: string) {
  return ["exchange-rate-history", workspaceId] as const;
}

export function useExchangeRateHistory(currencyId: string | undefined, range: AnalyticsRange) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: [...exchangeRateHistoryQueryKey(workspaceId), currencyId, range],
    enabled: currencyId !== undefined,
    queryFn: ({ signal }) =>
      api.get<ExchangeRateHistory>(`/api/workspaces/${workspaceId}/analytics/rates`, {
        query: {
          currency_id: currencyId,
          date_from: range.dateFrom,
          date_to: range.dateTo,
        },
        signal,
      }),
  });
}
