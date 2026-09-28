import { QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useMemo } from "react";
import { RouterProvider } from "react-router-dom";
import { type ApiClient, ApiClientProvider } from "@/shared/api";
import { createQueryClient, ErrorBoundary } from "@/shared/errors";
import { ThemeProvider, ToastProvider, useToast } from "@/shared/ui";

type Router = Parameters<typeof RouterProvider>[0]["router"];

/** Серверное состояние: глобальные ошибки запросов и мутаций показываются через `useToast`. */
function QueryProvider({ children }: { children: ReactNode }) {
  const toast = useToast();
  const client = useMemo(() => createQueryClient(toast), [toast]);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

/**
 * Композиция провайдеров: ErrorBoundary → тема (antd ConfigProvider) → toast (antd App) →
 * API-клиент → серверное состояние → роутер. Реализация `ApiClient` подставляется только здесь.
 */
export function App({ apiClient, router }: { apiClient: ApiClient; router: Router }) {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          <ApiClientProvider client={apiClient}>
            <QueryProvider>
              <RouterProvider router={router} />
            </QueryProvider>
          </ApiClientProvider>
        </ToastProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
