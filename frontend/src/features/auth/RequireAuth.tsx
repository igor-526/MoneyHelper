import { Spin } from "antd";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "./session";

function FullscreenSpinner() {
  return (
    <div
      style={{
        display: "flex",
        minHeight: "100dvh",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Spin size="large" />
    </div>
  );
}

/** Оборачивает защищённые маршруты. Пока сессия проверяется — спиннер (без мигания формы входа). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isChecking } = useSession();
  const location = useLocation();

  if (isChecking) return <FullscreenSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}
