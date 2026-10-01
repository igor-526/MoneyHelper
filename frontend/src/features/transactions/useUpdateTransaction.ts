import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Transaction, TransactionFormValues } from "./Transaction";
import { transactionsQueryKey } from "./useTransactions";
import { walletBalancesQueryKey } from "./useWalletBalances";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useUpdateTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: TransactionFormValues }) =>
      api.put<Transaction>(`/api/workspaces/${workspaceId}/transactions/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionsQueryKey(workspaceId) });
      queryClient.invalidateQueries({ queryKey: walletBalancesQueryKey(workspaceId) });
    },
  });
}
