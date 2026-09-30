import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { Transfer, TransferFormValues } from "./Transfer";
import { TRANSFERS_QUERY_KEY } from "./useTransfers";

/** Локальная копия ключа кэша балансов — см. комментарий в `useCreateTransfer.ts`. */
const WALLET_BALANCES_QUERY_KEY = ["wallet-balances"] as const;

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useUpdateTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: TransferFormValues }) =>
      api.put<Transfer>(`/api/transfers/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
