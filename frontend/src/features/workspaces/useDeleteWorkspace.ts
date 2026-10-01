import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { WORKSPACES_QUERY_KEY } from "./useWorkspaces";

/**
 * Удаление воркспейса — каскадное и безусловное на backend (020), без специфичных ошибок вроде 409
 * «есть операции» у кошельков/категорий, поэтому без `meta: { silent: true }` и без `onError`.
 */
export function useDeleteWorkspace() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/workspaces/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WORKSPACES_QUERY_KEY });
    },
  });
}
