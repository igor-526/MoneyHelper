import type { RouteObject } from "react-router-dom";
import { HealthPage } from "@/features/health/HealthPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { AppLayout } from "./layout/AppLayout";
import { NotFoundPage } from "./NotFoundPage";
import { RouteErrorElement } from "./RouteErrorElement";

export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    errorElement: <RouteErrorElement />,
    children: [
      { index: true, element: <HealthPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
