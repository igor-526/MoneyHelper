import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import { transfersQueryKey } from "./useTransfers";

/** Локальная копия ключа кэша балансов — см. комментарий в `useCreateTransfer.ts`. */
function walletBalancesQueryKey(workspaceId: string) {
  return ["wallet-balances", workspaceId] as const;
}

/**
 * Без `meta: { silent: true }` и без `onError` — по образцу `useDeleteTransaction`: специфичных ошибок удаления
 * перевода нет, глобальный обработчик покажет toast сам.
 */
export function useDeleteTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<undefined>(`/api/workspaces/${workspaceId}/transfers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transfersQueryKey(workspaceId) });
      queryClient.invalidateQueries({ queryKey: walletBalancesQueryKey(workspaceId) });
    },
  });
}
