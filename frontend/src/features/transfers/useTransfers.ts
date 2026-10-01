import { useQuery } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Transfer } from "./Transfer";

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

export function transfersQueryKey(workspaceId: string) {
  return ["transfers", workspaceId] as const;
}

function transferListKey(workspaceId: string, filters: TransferFilters, pagination: Pagination) {
  return [...transfersQueryKey(workspaceId), { ...filters, ...pagination }] as const;
}

/**
 * Список переводов растёт без ограничения (как список операций, 016), поэтому реальная серверная пагинация;
 * возвращает весь `Page<Transfer>` (не только `items`) — `total` нужен для пагинации.
 */
export function useTransfers(filters: TransferFilters, pagination: Pagination) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: transferListKey(workspaceId, filters, pagination),
    queryFn: ({ signal }) =>
      api.get<Page<Transfer>>(`/api/workspaces/${workspaceId}/transfers`, {
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
