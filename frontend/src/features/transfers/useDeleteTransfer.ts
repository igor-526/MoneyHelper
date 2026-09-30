import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { TRANSFERS_QUERY_KEY } from "./useTransfers";

/** Локальная копия ключа кэша балансов — см. комментарий в `useCreateTransfer.ts`. */
const WALLET_BALANCES_QUERY_KEY = ["wallet-balances"] as const;

/**
 * Без `meta: { silent: true }` и без `onError` — по образцу `useDeleteTransaction`: специфичных ошибок удаления
 * перевода нет, глобальный обработчик покажет toast сам.
 */
export function useDeleteTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/transfers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
