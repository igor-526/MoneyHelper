import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import { invalidateOperationCaches } from "./invalidateOperationCaches";

/**
 * Без `meta: { silent: true }` и без `onError` — 409 у операций не возникает, но паттерн
 * `useDeleteWallet`/`useDeleteCategory` сохранён для единообразия и на случай будущих правил (design.md).
 */
export function useDeleteTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<undefined>(`/api/workspaces/${workspaceId}/transactions/${id}`),
    onSuccess: () => {
      invalidateOperationCaches(queryClient, workspaceId);
    },
  });
}
