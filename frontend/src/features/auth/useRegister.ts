import { useMutation } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";
import type { User } from "./session";

export interface RegisterInput {
  email: string;
  password: string;
}

/** Регистрация не устанавливает сессию (по спецификации backend), поэтому кэш сессии не трогаем. */
export function useRegister() {
  const api = useApiClient();

  return useMutation({
    mutationFn: (input: RegisterInput) => api.post<User>("/api/auth/register", input),
    meta: { silent: true },
  });
}
