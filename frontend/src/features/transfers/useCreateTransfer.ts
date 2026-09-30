import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Transfer, TransferFormValues } from "./Transfer";
import { TRANSFERS_QUERY_KEY } from "./useTransfers";

/**
 * Локальная копия ключа кэша балансов — НЕ импорт `WALLET_BALANCES_QUERY_KEY` из `features/transactions`.
 * TanStack Query сравнивает `queryKey` структурно (по значению массива, не по ссылке на константу), поэтому
 * инвалидация по литералу `["wallet-balances"]` достигает того же эффекта, что и импортированная константа, без
 * первого в проекте прецедента кросс-фичевого импорта (`features/<feature>` самодостаточны, AGENTS.md).
 */
const WALLET_BALANCES_QUERY_KEY = ["wallet-balances"] as const;

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useCreateTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: TransferFormValues) => api.post<Transfer>("/api/transfers", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
