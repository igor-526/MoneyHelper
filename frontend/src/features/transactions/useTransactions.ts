import { useQuery } from "@tanstack/react-query";
import type { CategoryType } from "@/features/categories/Category";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Transaction } from "./Transaction";

export const TRANSACTIONS_QUERY_KEY = ["transactions"] as const;
export const DEFAULT_PAGE_SIZE = 20;

export interface TransactionFilters {
  walletId?: string;
  categoryId?: string;
  type?: CategoryType;
  dateFrom?: string; // ISO, начало выбранного дня
  dateTo?: string; // ISO, конец выбранного дня
}

interface Pagination {
  offset: number;
  limit: number;
}

function transactionsQueryKey(filters: TransactionFilters, pagination: Pagination) {
  return [...TRANSACTIONS_QUERY_KEY, { ...filters, ...pagination }] as const;
}

/**
 * В отличие от `useWallets`/`useCategories` — список операций растёт без ограничения, поэтому реальная
 * серверная пагинация; возвращает весь `Page<Transaction>` (не только `items`) — `total` нужен для пагинации.
 */
export function useTransactions(filters: TransactionFilters, pagination: Pagination) {
  const api = useApiClient();
  return useQuery({
    queryKey: transactionsQueryKey(filters, pagination),
    queryFn: ({ signal }) =>
      api.get<Page<Transaction>>("/api/transactions", {
        query: {
          wallet_id: filters.walletId,
          category_id: filters.categoryId,
          type: filters.type,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          limit: pagination.limit,
          offset: pagination.offset,
        },
        signal,
      }),
  });
}
