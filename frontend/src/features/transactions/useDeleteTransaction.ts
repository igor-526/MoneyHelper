import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { TRANSACTIONS_QUERY_KEY } from "./useTransactions";
import { WALLET_BALANCES_QUERY_KEY } from "./useWalletBalances";

/**
 * Без `meta: { silent: true }` и без `onError` — 409 у операций не возникает, но паттерн
 * `useDeleteWallet`/`useDeleteCategory` сохранён для единообразия и на случай будущих правил (design.md).
 */
export function useDeleteTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/transactions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSACTIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
