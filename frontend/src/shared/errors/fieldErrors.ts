import type { ApiError } from "../api/ApiError";

export const VALIDATION_MESSAGE = "Проверьте заполнение формы";
const MAX_LISTED = 3;

export interface AppliedFieldErrors {
  /** Сообщения для полей, которые есть в форме: имя поля -> тексты. */
  byField: Record<string, string[]>;
  /** Сообщения полей, которых нет в форме: чтобы не потерялись, они попадают в toast. */
  rest: string[];
  /** Готовый текст toast: «Проверьте заполнение формы» и, если есть, остаток. */
  toastMessage: string;
}

function formatToast(rest: string[]): string {
  if (rest.length === 0) return VALIDATION_MESSAGE;
  const listed = rest.slice(0, MAX_LISTED).join("; ");
  const suffix = rest.length > MAX_LISTED ? "…" : "";
  return `${VALIDATION_MESSAGE}: ${listed}${suffix}`;
}

/** Разносит ошибки валидации `ApiError` по полям формы; остальные сообщения возвращает в `rest`. */
export function applyFieldErrors(
  error: ApiError,
  knownFields: readonly string[],
): AppliedFieldErrors {
  const known = new Set(knownFields);
  const byField: Record<string, string[]> = {};
  const rest: string[] = [];

  for (const [field, messages] of Object.entries(error.fieldErrors)) {
    if (known.has(field)) {
      byField[field] = messages;
    } else {
      rest.push(...messages.map((message) => `${field}: ${message}`));
    }
  }
  if (error.detail) rest.push(error.detail);

  return { byField, rest, toastMessage: formatToast(rest) };
}
