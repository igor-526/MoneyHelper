import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiError } from "../api/ApiError";
import type { ToastApi } from "../ui/toast/types";
import { createErrorHandler } from "./handleApiError";

const RETRYABLE_KINDS = new Set(["network", "server", "timeout"]);

/** Запросы на чтение повторяются один раз и только при сбоях сети/сервера; мутации не повторяются. */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  return failureCount < 1 && error instanceof ApiError && RETRYABLE_KINDS.has(error.kind);
}

/** `QueryClient` с глобальным показом toast для любой ошибки запроса и мутации. */
export function createQueryClient(
  toast: ToastApi,
  options?: { onUnauthorized?: () => void },
): QueryClient {
  const handle = createErrorHandler(toast, options);
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => handle(error, query.meta),
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _onMutateResult, mutation) => handle(error, mutation.meta),
    }),
    defaultOptions: {
      queries: { retry: shouldRetryQuery, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}
