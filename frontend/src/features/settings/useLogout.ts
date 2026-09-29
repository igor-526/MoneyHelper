import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SESSION_QUERY_KEY } from "@/features/auth/session";
import { useApiClient } from "@/shared/api";

/**
 * Сессия сбрасывается независимо от результата запроса: backend отвечает 204 почти всегда (logout
 * не бросает ошибку без сессии), а при сетевом сбое cookies всё равно истекут по TTL.
 */
export function useLogout() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post<undefined>("/api/auth/logout"),
    onSettled: () => {
      queryClient.setQueryData(SESSION_QUERY_KEY, null);
    },
  });
}
