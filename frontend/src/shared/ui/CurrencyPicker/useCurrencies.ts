import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Page } from "@/shared/api";
import { type CurrencyDto, mapCurrency } from "./Currency";

export const CURRENCIES_QUERY_KEY = ["currencies"] as const;

/** Справочник валют мал (сейчас 3), поэтому одной страницы с максимальным limit достаточно. */
export function useCurrencies() {
  const api = useApiClient();
  return useQuery({
    queryKey: CURRENCIES_QUERY_KEY,
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<CurrencyDto>>("/api/currencies", {
        query: { limit: 100, offset: 0 },
        signal,
      });
      return page.items.map(mapCurrency);
    },
  });
}
