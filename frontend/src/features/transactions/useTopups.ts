import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Transaction } from "./Transaction";
import type { OperationFilters, OperationPagination } from "./useTransactions";

export function topupsQueryKey(workspaceId: string) {
  return ["topups", workspaceId] as const;
}

/** Список пополнений (`GET /topups`) с теми же фильтрами и пагинацией, что и у расходов. */
export function useTopups(filters: OperationFilters, pagination: OperationPagination) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: [...topupsQueryKey(workspaceId), { ...filters, ...pagination }],
    queryFn: ({ signal }) =>
      api.get<Page<Transaction>>(`/api/workspaces/${workspaceId}/topups`, {
        query: {
          wallet_id: filters.walletId,
          category_id: filters.categoryId,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          limit: pagination.limit,
          offset: pagination.offset,
        },
        signal,
      }),
  });
}
