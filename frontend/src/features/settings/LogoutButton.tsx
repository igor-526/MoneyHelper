import { Button } from "antd";
import { Icon } from "@/shared/ui";
import { useLogout } from "./useLogout";

/**
 * Не переходит на `/login` сама: `useLogout` очищает кэш сессии, а `RequireAuth` (уже подписан на неё)
 * реагирует на это сам — тот же источник истины, что и для `GuestOnly`/`LoginPage` (см. design.md), иначе
 * навигация здесь гонялась бы с реактивным редиректом `RequireAuth` за тем, что окажется в `state.from`.
 */
export function LogoutButton() {
  const logout = useLogout();

  return (
    <Button
      block
      danger
      icon={<Icon name="log-out" />}
      loading={logout.isPending}
      onClick={() => logout.mutate()}
    >
      Выйти
    </Button>
  );
}
