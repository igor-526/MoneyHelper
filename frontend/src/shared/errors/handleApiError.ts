import { ApiError } from "../api/ApiError";
import type { ToastApi } from "../ui/toast/types";
import type { ErrorMeta } from "./meta";
import { resolveErrorMessage } from "./messages";

/** Приводит любую ошибку к `ApiError`: ошибка, не связанная с API, не должна пропасть молча. */
export function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError({ kind: "unknown", status: null });
}

/** Глобальный обработчик: показывает toast, если действие не отключило его через `meta.silent`. */
export function createErrorHandler(toast: ToastApi) {
  return (error: unknown, meta?: ErrorMeta): void => {
    if (meta?.silent) return;
    toast.error(resolveErrorMessage(toApiError(error), meta?.errorMessages));
  };
}
