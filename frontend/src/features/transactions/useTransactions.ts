import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Transaction } from "./Transaction";

export const DEFAULT_PAGE_SIZE = 20;

/** Фильтры списков расходов и пополнений; тип задаётся самим списком. */
export interface OperationFilters {
  walletId?: string;
  categoryId?: string;
  dateFrom?: string; // ISO, начало выбранного дня
  dateTo?: string; // ISO, конец выбранного дня
}

export interface OperationPagination {
  offset: number;
  limit: number;
}

export function transactionsQueryKey(workspaceId: string) {
  return ["transactions", workspaceId] as const;
}

function transactionListKey(
  workspaceId: string,
  filters: OperationFilters,
  pagination: OperationPagination,
) {
  return [...transactionsQueryKey(workspaceId), { ...filters, ...pagination }] as const;
}

/**
 * Список расходов (`GET /transactions` возвращает только расходы). В отличие от `useWallets`/`useCategories` — список операций растёт без ограничения, поэтому реальная
 * серверная пагинация; возвращает весь `Page<Transaction>` (не только `items`) — `total` нужен для пагинации.
 */
export function useTransactions(filters: OperationFilters, pagination: OperationPagination) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: transactionListKey(workspaceId, filters, pagination),
    queryFn: ({ signal }) =>
      api.get<Page<Transaction>>(`/api/workspaces/${workspaceId}/transactions`, {
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
