import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export const SESSION_QUERY_KEY = ["auth", "session"] as const;

/**
 * Сессия — обычный запрос TanStack Query, а не отдельный React-контекст. `meta.silent: true`: 401 для
 * анонимного посетителя при первом визите — нормальное состояние, а не ошибка, глобальный toast тут неуместен.
 */
export function useSession() {
  const api = useApiClient();
  const query = useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: ({ signal }) => api.get<User>("/api/auth/me", { signal }),
    retry: false,
    meta: { silent: true },
  });

  return {
    user: query.data ?? null,
    isAuthenticated: query.data != null,
    isChecking: query.isPending,
  };
}
