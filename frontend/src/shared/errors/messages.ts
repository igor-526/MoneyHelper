import type { ApiError, ApiErrorKind } from "../api/ApiError";
import { applyFieldErrors } from "./fieldErrors";
import type { ErrorMeta } from "./meta";

type MessageBuilder = (error: ApiError) => string;

/** Сообщения по умолчанию: новый вид ошибки — новая строка таблицы, без цепочек `if`. */
const MESSAGE_BUILDERS: Record<ApiErrorKind, MessageBuilder> = {
  validation: (error) =>
    Object.keys(error.fieldErrors).length === 0 && error.detail
      ? error.detail
      : applyFieldErrors(error, []).toastMessage,
  unauthorized: () => "Сессия истекла, войдите снова",
  forbidden: () => "Недостаточно прав для этого действия",
  not_found: (error) => error.detail ?? "Не найдено",
  conflict: (error) => error.detail ?? "Конфликт данных, обновите страницу",
  server: () => "Ошибка сервера, попробуйте позже",
  network: () => "Нет соединения с сервером",
  timeout: () => "Сервер не отвечает, попробуйте позже",
  unknown: () => "Что-то пошло не так",
};

export function resolveErrorMessage(
  error: ApiError,
  overrides?: ErrorMeta["errorMessages"],
): string {
  if (typeof overrides === "string") return overrides;
  return overrides?.[error.kind] ?? MESSAGE_BUILDERS[error.kind](error);
}
