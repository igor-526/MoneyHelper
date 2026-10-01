import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Workspace } from "./Workspace";

export const WORKSPACES_QUERY_KEY = ["workspaces"] as const;

/** Персональный объём воркспейсов пользователя мал (тот же аргумент, что у `useWallets`). */
export function useWorkspaces() {
  const api = useApiClient();
  return useQuery({
    queryKey: WORKSPACES_QUERY_KEY,
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Workspace>>("/api/workspaces", {
        query: { limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
