import type { RouteObject } from "react-router-dom";
import { GuestOnly } from "@/features/auth/GuestOnly";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { HealthPage } from "@/features/health/HealthPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { WalletsPage } from "@/features/wallets/WalletsPage";
import { AppLayout } from "./layout/AppLayout";
import { NotFoundPage } from "./NotFoundPage";
import { RouteErrorElement } from "./RouteErrorElement";

export const routes: RouteObject[] = [
  {
    // Публичные маршруты: авторизованный пользователь сюда не попадает (GuestOnly уводит на «/»).
    element: <GuestOnly />,
    children: [
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
    ],
  },
  {
    // Все остальные маршруты, включая неизвестные, требуют активную сессию.
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    errorElement: <RouteErrorElement />,
    children: [
      { index: true, element: <HealthPage /> },
      { path: "wallets", element: <WalletsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
