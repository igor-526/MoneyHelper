import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { useCurrentWorkspaceId } from "@/features/workspaces/WorkspaceContext";
import type { Wallet, WalletFormValues } from "./Wallet";
import { walletsQueryKey } from "./useWallets";

/** 400 по полям обрабатывает сама форма (`applyFieldErrors`), поэтому глобальный toast отключён. */
export function useUpdateWallet() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const workspaceId = useCurrentWorkspaceId();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: WalletFormValues }) =>
      api.put<Wallet>(`/api/workspaces/${workspaceId}/wallets/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: walletsQueryKey(workspaceId) });
    },
  });
}
