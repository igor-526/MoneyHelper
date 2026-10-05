import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import { invalidateOperationCaches } from "./invalidateOperationCaches";
import type { Transaction, TransactionFormValues } from "./Transaction";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useCreateTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (values: TransactionFormValues) =>
      api.post<Transaction>(`/api/workspaces/${workspaceId}/transactions`, values),
    meta: { silent: true },
    onSuccess: () => {
      invalidateOperationCaches(queryClient, workspaceId);
    },
  });
}
