import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import type { Wallet } from "./Wallet";

export const WALLETS_QUERY_KEY = ["wallets"] as const;

/** Персональный объём кошельков пользователя мал, поэтому одной страницы с максимальным limit достаточно. */
export function useWallets() {
  const api = useApiClient();
  return useQuery({
    queryKey: WALLETS_QUERY_KEY,
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Wallet>>("/api/wallets", {
        query: { limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
