import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Transfer, TransferFormValues } from "./Transfer";
import { invalidateTransferCaches } from "./invalidateTransferCaches";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useCreateTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (values: TransferFormValues) =>
      api.post<Transfer>(`/api/workspaces/${workspaceId}/transfers`, values),
    meta: { silent: true },
    onSuccess: () => invalidateTransferCaches(queryClient, workspaceId),
  });
}
