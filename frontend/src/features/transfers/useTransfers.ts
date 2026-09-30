import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Transfer } from "./Transfer";

export const TRANSFERS_QUERY_KEY = ["transfers"] as const;
export const DEFAULT_PAGE_SIZE = 20;

export interface TransferFilters {
  walletId?: string;
  dateFrom?: string; // ISO, начало выбранного дня
  dateTo?: string; // ISO, конец выбранного дня
}

interface Pagination {
  offset: number;
  limit: number;
}

function transfersQueryKey(filters: TransferFilters, pagination: Pagination) {
  return [...TRANSFERS_QUERY_KEY, { ...filters, ...pagination }] as const;
}

/**
 * Список переводов растёт без ограничения (как список операций, 016), поэтому реальная серверная пагинация;
 * возвращает весь `Page<Transfer>` (не только `items`) — `total` нужен для пагинации.
 */
export function useTransfers(filters: TransferFilters, pagination: Pagination) {
  const api = useApiClient();
  return useQuery({
    queryKey: transfersQueryKey(filters, pagination),
    queryFn: ({ signal }) =>
      api.get<Page<Transfer>>("/api/transfers", {
        query: {
          wallet_id: filters.walletId,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          limit: pagination.limit,
          offset: pagination.offset,
        },
        signal,
      }),
  });
}
