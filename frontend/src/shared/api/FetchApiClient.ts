import { type ApiRequest, BaseApiClient } from "./ApiClient";
import { ApiError } from "./ApiError";
import { parseApiError } from "./parseApiError";

export const DEFAULT_TIMEOUT_MS = 15_000;

export interface FetchApiClientOptions {
  baseUrl: string;
  timeoutMs?: number;
  /** Вызывается при 401; `true` — сессия обновлена, запрос будет повторён один раз. */
  onUnauthorized?: () => Promise<boolean>;
  fetchImpl?: typeof fetch;
}

/** Реализация `ApiClient` на `fetch`: cookies, JSON, таймаут, нормализация ошибок в `ApiError`. */
export class FetchApiClient extends BaseApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly onUnauthorized?: () => Promise<boolean>;
  private readonly fetchImpl: typeof fetch;

  constructor(options: FetchApiClientOptions) {
    super();
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.onUnauthorized = options.onUnauthorized;
    this.fetchImpl = options.fetchImpl ?? ((...args) => fetch(...args));
  }

  protected request<T>(request: ApiRequest): Promise<T> {
    return this.send<T>(request, true);
  }

  private async send<T>(request: ApiRequest, allowRetry: boolean): Promise<T> {
    const response = await this.execute(request);

    if (response.status === 401 && allowRetry && this.onUnauthorized) {
      if (await this.refreshSession()) {
        return this.send<T>(request, false);
      }
    }
    if (!response.ok) {
      throw parseApiError(response.status, await readBody(response));
    }
    return (await readBody(response)) as T;
  }

  private async refreshSession(): Promise<boolean> {
    try {
      return (await this.onUnauthorized?.()) === true;
    } catch {
      return false;
    }
  }

  private async execute(request: ApiRequest): Promise<Response> {
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.timeoutMs);
    const forwardAbort = () => controller.abort();
    request.signal?.addEventListener("abort", forwardAbort);
    if (request.signal?.aborted) controller.abort();

    try {
      return await this.fetchImpl(this.buildUrl(request), {
        method: request.method,
        credentials: "include",
        headers: request.body === undefined ? undefined : { "Content-Type": "application/json" },
        body: request.body === undefined ? undefined : JSON.stringify(request.body),
        signal: controller.signal,
      });
    } catch (error) {
      if (timedOut) throw new ApiError({ kind: "timeout", status: null });
      if (request.signal?.aborted) throw error;
      throw new ApiError({ kind: "network", status: null });
    } finally {
      clearTimeout(timer);
      request.signal?.removeEventListener("abort", forwardAbort);
    }
  }

  private buildUrl({ path, query }: ApiRequest): string {
    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    if (!query) return url;
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) params.set(key, String(value));
    }
    const search = params.toString();
    return search ? `${url}?${search}` : url;
  }
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text().catch(() => "");
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}
