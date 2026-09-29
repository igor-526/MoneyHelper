import { useMutation } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

/** `meta.silent`: компонент сам привязывает ошибки к полям и подбирает текст под контекст смены пароля. */
export function useChangePassword() {
  const api = useApiClient();

  return useMutation({
    mutationFn: (input: ChangePasswordInput) => api.post<undefined>("/api/auth/password", input),
    meta: { silent: true },
  });
}
