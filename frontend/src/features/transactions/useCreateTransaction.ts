import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Transaction, TransactionFormValues } from "./Transaction";
import { TRANSACTIONS_QUERY_KEY } from "./useTransactions";
import { WALLET_BALANCES_QUERY_KEY } from "./useWalletBalances";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useCreateTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: TransactionFormValues) =>
      api.post<Transaction>("/api/transactions", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSACTIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
