import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import { invalidateOperationCaches } from "./invalidateOperationCaches";
import type { Transaction, TopupFormValues } from "./Transaction";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useUpdateTopup() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: TopupFormValues }) =>
      api.put<Transaction>(`/api/workspaces/${workspaceId}/topups/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      invalidateOperationCaches(queryClient, workspaceId);
    },
  });
}
