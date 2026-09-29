import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "./session";

interface LocationState {
  from?: { pathname: string; search: string };
}

/**
 * Группа публичных маршрутов (`/login`, `/register`): авторизованный пользователь сюда не попадает.
 *
 * Единственное место, которое редиректит на «куда шёл пользователь» при появлении сессии — и для прямого
 * захода на `/login` под сессией, и для успешного входа (он сам никуда не переходит, а лишь обновляет кэш
 * сессии). Два редиректа на одно и то же событие гонялись бы за одним `router.navigate`.
 */
export function GuestOnly() {
  const { isAuthenticated, isChecking } = useSession();
  const location = useLocation();

  if (isChecking) return null;
  if (isAuthenticated) {
    const from = (location.state as LocationState | null)?.from;
    return <Navigate to={from ? `${from.pathname}${from.search}` : "/"} replace />;
  }
  return <Outlet />;
}
