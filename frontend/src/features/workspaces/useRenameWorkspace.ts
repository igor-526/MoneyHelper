import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Workspace, WorkspaceFormValues } from "./Workspace";
import { WORKSPACES_QUERY_KEY } from "./useWorkspaces";

/** `PUT` — полная замена `name`, как и на backend. 400 по полям обрабатывает сама форма. */
export function useRenameWorkspace() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: WorkspaceFormValues }) =>
      api.put<Workspace>(`/api/workspaces/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WORKSPACES_QUERY_KEY });
    },
  });
}
