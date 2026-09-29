import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Category, CategoryFormValues } from "./Category";
import { CATEGORIES_QUERY_KEY } from "./useCategories";

/** 400 по полям и 409 на дубль названия обрабатывает сама форма, поэтому глобальный toast отключён. */
export function useUpdateCategory() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: CategoryFormValues }) =>
      api.put<Category>(`/api/categories/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });
}
