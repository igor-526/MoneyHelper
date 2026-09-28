export type ApiErrorKind =
  | "validation"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "server"
  | "network"
  | "timeout"
  | "unknown";

export type FieldErrors = Record<string, string[]>;

export interface ApiErrorInit {
  kind: ApiErrorKind;
  status: number | null;
  detail?: string | null;
  fieldErrors?: FieldErrors;
}

/** Единый тип ошибки API: любой сбой запроса (ответ с ошибкой, сеть, таймаут) приводится к нему. */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly detail: string | null;
  readonly fieldErrors: FieldErrors;

  constructor({ kind, status, detail = null, fieldErrors = {} }: ApiErrorInit) {
    super(detail ?? `API error: ${kind}${status === null ? "" : ` (${status})`}`);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }
}
