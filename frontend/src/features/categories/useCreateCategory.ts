import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import type { Category, CategoryFormValues } from "./Category";
import { categoriesQueryKey } from "./useCategories";

/** 400 по полям и 409 на дубль названия обрабатывает сама форма, поэтому глобальный toast отключён. */
export function useCreateCategory() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (values: CategoryFormValues) =>
      api.post<Category>(`/api/workspaces/${workspaceId}/categories`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: categoriesQueryKey(workspaceId) });
    },
  });
}
