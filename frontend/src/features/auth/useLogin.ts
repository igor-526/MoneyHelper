import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import { SESSION_QUERY_KEY, type User } from "./session";

export interface LoginInput {
  email: string;
  password: string;
}

/**
 * `meta.silent: true`: компонент сам решает, как показать ошибку (инлайн для unauthorized, toast для
 * остальных) — см. `LoginPage`. `/login` уже возвращает пользователя, поэтому лишний запрос `/me` не нужен.
 */
export function useLogin() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: LoginInput) => api.post<User>("/api/auth/login", input),
    meta: { silent: true },
    onSuccess: (user) => {
      queryClient.setQueryData(SESSION_QUERY_KEY, user);
    },
  });
}
