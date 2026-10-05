import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import { invalidateTransferCaches } from "./invalidateTransferCaches";

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
    onSuccess: () => invalidateTransferCaches(queryClient, workspaceId),
  });
}
