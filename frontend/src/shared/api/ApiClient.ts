export interface RequestOptions {
  query?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
}

/**
 * Интерфейс API-клиента. Компоненты и hooks зависят от него, а не от `fetch`;
 * реализация подставляется на верхнем уровне (`ApiClientProvider`).
 */
export interface ApiClient {
  get<T>(path: string, options?: RequestOptions): Promise<T>;
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>;
  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>;
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>;
  delete<T>(path: string, options?: RequestOptions): Promise<T>;
}

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiRequest extends RequestOptions {
  method: HttpMethod;
  path: string;
  body?: unknown;
}

/** Заготовка: глаголы реализованы через единственный `request`, который переопределяет наследник. */
export abstract class BaseApiClient implements ApiClient {
  protected abstract request<T>(request: ApiRequest): Promise<T>;

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>({ ...options, method: "GET", path });
  }

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>({ ...options, method: "POST", path, body });
  }

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>({ ...options, method: "PUT", path, body });
  }

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>({ ...options, method: "PATCH", path, body });
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>({ ...options, method: "DELETE", path });
  }
}
