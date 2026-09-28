import type { ApiErrorKind } from "../api/ApiError";

/** Настройки обработки ошибок конкретного запроса/мутации (`meta` в TanStack Query). */
export interface ErrorMeta extends Record<string, unknown> {
  /** Свой текст toast: общий для любой ошибки или по виду ошибки. */
  errorMessages?: string | Partial<Record<ApiErrorKind, string>>;
  /**
   * Отключает глобальный toast. Действие обязано обработать ошибку явно
   * (например, показать ошибки по полям формы через `applyFieldErrors`).
   */
  silent?: boolean;
}

declare module "@tanstack/react-query" {
  interface Register {
    queryMeta: ErrorMeta;
    mutationMeta: ErrorMeta;
  }
}
