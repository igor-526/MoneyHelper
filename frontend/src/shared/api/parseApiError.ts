import { ApiError, type ApiErrorKind, type FieldErrors } from "./ApiError";

const KIND_BY_STATUS: Record<number, ApiErrorKind> = {
  400: "validation",
  401: "unauthorized",
  403: "forbidden",
  404: "not_found",
  409: "conflict",
};

export function kindFromStatus(status: number): ApiErrorKind {
  const known = KIND_BY_STATUS[status];
  if (known) return known;
  return status >= 500 ? "server" : "unknown";
}

interface ValidationItem {
  loc?: unknown;
  msg?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Имя поля формы из `loc` pydantic: ведущий сегмент `body` отбрасывается, остальные склеиваются точкой. */
function fieldName(loc: unknown): string {
  if (!Array.isArray(loc)) return "";
  const parts = loc.map(String);
  if (parts[0] === "body") parts.shift();
  return parts.join(".");
}

function parseValidationItems(items: unknown[]): {
  fieldErrors: FieldErrors;
  detail: string | null;
} {
  const fieldErrors: FieldErrors = {};
  const general: string[] = [];
  for (const item of items) {
    if (!isRecord(item)) continue;
    const { loc, msg } = item as ValidationItem;
    if (typeof msg !== "string") continue;
    const name = fieldName(loc);
    if (name) {
      (fieldErrors[name] ??= []).push(msg);
    } else {
      general.push(msg);
    }
  }
  return { fieldErrors, detail: general.length > 0 ? general.join("; ") : null };
}

/** Превращает статус и тело ответа backend (`{"detail": ...}`) в `ApiError`. */
export function parseApiError(status: number, body: unknown): ApiError {
  const kind = kindFromStatus(status);
  const rawDetail = isRecord(body) ? body.detail : undefined;

  if (typeof rawDetail === "string") {
    return new ApiError({ kind, status, detail: rawDetail });
  }
  if (Array.isArray(rawDetail)) {
    const { fieldErrors, detail } = parseValidationItems(rawDetail);
    return new ApiError({ kind, status, detail, fieldErrors });
  }
  return new ApiError({ kind, status });
}
