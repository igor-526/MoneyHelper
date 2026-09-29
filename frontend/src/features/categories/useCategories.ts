import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Category, CategoryType } from "./Category";

export const CATEGORIES_QUERY_KEY = ["categories"] as const;

function categoryQueryKey(type: CategoryType | undefined) {
  return [...CATEGORIES_QUERY_KEY, type ?? "all"] as const;
}

/** Персональный объём категорий пользователя мал, поэтому одной страницы с максимальным limit достаточно. */
export function useCategories(type: CategoryType | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: categoryQueryKey(type),
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Category>>("/api/categories", {
        query: { type, limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
