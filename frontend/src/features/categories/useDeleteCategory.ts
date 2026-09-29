import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { CATEGORIES_QUERY_KEY } from "./useCategories";

/**
 * Без `meta: { silent: true }` и без `onError`: единственная специфичная ошибка удаления — 409
 * «есть операции», её уже показывает `MESSAGE_BUILDERS.conflict` глобального обработчика (design.md).
 */
export function useDeleteCategory() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/categories/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });
}
