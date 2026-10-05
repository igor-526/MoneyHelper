import { Navigate, type RouteObject } from "react-router-dom";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { GuestOnly } from "@/features/auth/GuestOnly";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { CategoriesPage } from "@/features/categories/CategoriesPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { TransactionsPage } from "@/features/transactions/TransactionsPage";
import { WalletsPage } from "@/features/wallets/WalletsPage";
import { RequireWorkspace } from "@/features/workspaces/RequireWorkspace";
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
        <RequireWorkspace>
          <AppLayout />
        </RequireWorkspace>
      </RequireAuth>
    ),
    errorElement: <RouteErrorElement />,
    children: [
      { index: true, element: <Navigate to="/transactions" replace /> },
      { path: "wallets", element: <WalletsPage /> },
      { path: "categories", element: <CategoriesPage /> },
      { path: "transactions", element: <TransactionsPage /> },
      { path: "transfers", element: <Navigate to="/transactions?tab=transfer" replace /> },
      { path: "analytics", element: <AnalyticsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
