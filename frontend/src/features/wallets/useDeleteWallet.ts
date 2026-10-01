import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { walletsQueryKey } from "./useWallets";

/**
 * Без `meta: { silent: true }` и без `onError`: единственная специфичная ошибка удаления — 409
 * «есть операции», её уже показывает `MESSAGE_BUILDERS.conflict` глобального обработчика (design.md).
 */
export function useDeleteWallet() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<undefined>(`/api/workspaces/${workspaceId}/wallets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: walletsQueryKey(workspaceId) });
    },
  });
}
