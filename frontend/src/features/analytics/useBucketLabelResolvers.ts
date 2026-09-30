import { useMemo } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { useCurrencies } from "@/shared/ui";
import type { GroupBy } from "./Analytics";

/** По образцу backend `DIMENSIONS` (`core/services/analytics_dimensions.py`): реестр резолверов подписи корзины
 *  строится из трёх `Map`, а не ветвлением `if group_by === ...`. */
export function useBucketLabelResolvers(): Record<GroupBy, (key: string) => string | undefined> {
  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories(undefined);
  const { data: currencies = [] } = useCurrencies();

  const walletNameById = useMemo(() => new Map(wallets.map((w) => [w.id, w.name])), [wallets]);
  const categoryNameById = useMemo(
    () => new Map(categories.map((c) => [c.id, c.name])),
    [categories],
  );
  const currencyCodeById = useMemo(
    () => new Map(currencies.map((c) => [c.id, c.code])),
    [currencies],
  );

  return useMemo(
    () => ({
      wallet: (key: string) => walletNameById.get(key),
      category: (key: string) => categoryNameById.get(key),
      currency: (key: string) => currencyCodeById.get(key),
    }),
    [walletNameById, categoryNameById, currencyCodeById],
  );
}
