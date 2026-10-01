import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import type { Category, CategoryType } from "./Category";

export function categoriesQueryKey(workspaceId: string) {
  return ["categories", workspaceId] as const;
}

export function categoryListKey(workspaceId: string, type: CategoryType | undefined) {
  return [...categoriesQueryKey(workspaceId), type ?? "all"] as const;
}

/** Персональный объём категорий пользователя мал, поэтому одной страницы с максимальным limit достаточно. */
export function useCategories(type: CategoryType | undefined) {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: categoryListKey(workspaceId, type),
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Category>>(`/api/workspaces/${workspaceId}/categories`, {
        query: { type, limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
