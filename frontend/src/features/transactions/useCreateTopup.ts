import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Transaction, TopupFormValues } from "./Transaction";
import { TRANSACTIONS_QUERY_KEY } from "./useTransactions";
import { WALLET_BALANCES_QUERY_KEY } from "./useWalletBalances";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useCreateTopup() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: TopupFormValues) =>
      api.post<Transaction>("/api/transactions/topups", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSACTIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
