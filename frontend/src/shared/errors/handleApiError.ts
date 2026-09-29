import { ApiError } from "../api/ApiError";
import type { ToastApi } from "../ui/toast/types";
import type { ErrorMeta } from "./meta";
import { resolveErrorMessage } from "./messages";

/** Приводит любую ошибку к `ApiError`: ошибка, не связанная с API, не должна пропасть молча. */
export function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError({ kind: "unknown", status: null });
}

/** Глобальный обработчик: показывает toast, если действие не отключило его через `meta.silent`. */
export function createErrorHandler(toast: ToastApi, options?: { onUnauthorized?: () => void }) {
  return (error: unknown, meta?: ErrorMeta): void => {
    if (meta?.silent) return;
    const apiError = toApiError(error);
    toast.error(resolveErrorMessage(apiError, meta?.errorMessages));
    // Сюда попадают только «настоящие» истечения сессии во время работы: проверка `/me` при
    // первом визите отключает toast через `meta.silent` и этот колбэк не вызывает.
    if (apiError.kind === "unauthorized") options?.onUnauthorized?.();
  };
}
