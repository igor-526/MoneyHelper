import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";

/** Есть ли в воркспейсе кошельки: от этого зависит, можно ли менять его валюту (backend вернёт 409). */
export function useWorkspaceHasWallets(workspaceId: string | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: ["workspace-has-wallets", workspaceId],
    enabled: workspaceId !== undefined,
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<unknown>>(`/api/workspaces/${workspaceId}/wallets`, {
        query: { limit: 1, offset: 0 },
        signal,
      });
      return page.total > 0;
    },
  });
}
