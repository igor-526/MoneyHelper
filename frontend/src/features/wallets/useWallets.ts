import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import type { Wallet } from "./Wallet";

export function walletsQueryKey(workspaceId: string) {
  return ["wallets", workspaceId] as const;
}

/** Персональный объём кошельков пользователя мал, поэтому одной страницы с максимальным limit достаточно. */
export function useWallets() {
  const api = useApiClient();
  const workspaceId = useCurrentWorkspaceId();
  return useQuery({
    queryKey: walletsQueryKey(workspaceId),
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Wallet>>(`/api/workspaces/${workspaceId}/wallets`, {
        query: { limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
