import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { AnalyticsFilters, AnalyticsResult } from "./Analytics";

export function analyticsQueryKey(workspaceId: string) {
  return ["analytics", workspaceId] as const;
}

export function useAnalytics(filters: AnalyticsFilters) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: [...analyticsQueryKey(workspaceId), filters],
    queryFn: ({ signal }) =>
      api.get<AnalyticsResult>(`/api/workspaces/${workspaceId}/analytics`, {
        query: {
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          group_by: filters.groupBy,
          type: filters.type,
          wallet_id: filters.walletId,
          category_id: filters.categoryId,
        },
        signal,
      }),
  });
}
