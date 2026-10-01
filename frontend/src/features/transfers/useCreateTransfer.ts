import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import { useApiClient } from "@/shared/api";
import type { Transfer, TransferFormValues } from "./Transfer";
import { transfersQueryKey } from "./useTransfers";

/**
 * Локальная копия ключа кэша балансов — НЕ импорт `walletBalancesQueryKey` из `features/transactions`.
 * TanStack Query сравнивает `queryKey` структурно (по значению массива, не по ссылке на функцию), поэтому
 * локальный `["wallet-balances", workspaceId]` достигает того же эффекта, что и импортированная функция, без
 * первого в проекте прецедента кросс-фичевого импорта (`features/<feature>` самодостаточны, AGENTS.md).
 */
function walletBalancesQueryKey(workspaceId: string) {
  return ["wallet-balances", workspaceId] as const;
}

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useCreateTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: (values: TransferFormValues) =>
      api.post<Transfer>(`/api/workspaces/${workspaceId}/transfers`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transfersQueryKey(workspaceId) });
      queryClient.invalidateQueries({ queryKey: walletBalancesQueryKey(workspaceId) });
    },
  });
}
