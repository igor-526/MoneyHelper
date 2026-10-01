import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Transfer, TransferFormValues } from "./Transfer";
import { transfersQueryKey } from "./useTransfers";

/** Локальная копия ключа кэша балансов — см. комментарий в `useCreateTransfer.ts`. */
function walletBalancesQueryKey(workspaceId: string) {
  return ["wallet-balances", workspaceId] as const;
}

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useUpdateTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: TransferFormValues }) =>
      api.put<Transfer>(`/api/workspaces/${workspaceId}/transfers/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transfersQueryKey(workspaceId) });
      queryClient.invalidateQueries({ queryKey: walletBalancesQueryKey(workspaceId) });
    },
  });
}
