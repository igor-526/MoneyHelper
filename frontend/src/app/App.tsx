import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useMemo } from "react";
import { RouterProvider } from "react-router-dom";
import { SESSION_QUERY_KEY } from "@/features/auth/session";
import { type ApiClient, ApiClientProvider } from "@/shared/api";
import { createQueryClient, ErrorBoundary } from "@/shared/errors";
import { ThemeProvider, ToastProvider, useToast } from "@/shared/ui";

type Router = Parameters<typeof RouterProvider>[0]["router"];

/**
 * Серверное состояние: глобальные ошибки запросов и мутаций показываются через `useToast`. Истёкшая
 * сессия (401 после неудачного обновления, у запроса без `meta.silent`) очищает кэш сессии — `RequireAuth`
 * реагирует на это сам и уводит на `/login` (с сохранением текущего пути, как при обычном заходе без сессии).
 */
function QueryProvider({ children }: { children: ReactNode }) {
  const toast = useToast();
  const client = useMemo(() => {
    // `instance` замыкается колбэком до того, как ей присвоено значение — она вызывается только позже,
    // при реальном 401, когда переменная уже определена.
    const instance: QueryClient = createQueryClient(toast, {
      onUnauthorized: () => instance.setQueryData(SESSION_QUERY_KEY, null),
    });
    return instance;
  }, [toast]);
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
