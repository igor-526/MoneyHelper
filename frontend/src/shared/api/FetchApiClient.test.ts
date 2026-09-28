import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./ApiError";
import { FetchApiClient } from "./FetchApiClient";

function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

function createClient(fetchImpl: typeof fetch, extra: object = {}) {
  return new FetchApiClient({ baseUrl: "http://api.test/", fetchImpl, ...extra });
}

async function catchError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("ожидалась ошибка");
}

describe("FetchApiClient", () => {
  it("отправляет запрос с cookies на адрес из конфигурации", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { status: "ok" }));
    const result = await createClient(fetchImpl).get("/health");

    expect(result).toEqual({ status: "ok" });
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://api.test/health",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
  });

  it("передаёт JSON-тело и query-параметры", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, {}));
    await createClient(fetchImpl).post(
      "/items",
      { name: "a" },
      { query: { limit: 5, skip: undefined } },
    );

    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/items?limit=5");
    expect(init.body).toBe('{"name":"a"}');
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("возвращает undefined для пустого ответа (204)", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    await expect(createClient(fetchImpl).delete("/items/1")).resolves.toBeUndefined();
  });

  it.each([
    [400, "validation"],
    [401, "unauthorized"],
    [403, "forbidden"],
    [404, "not_found"],
    [409, "conflict"],
    [500, "server"],
  ] as const)("ответ %s превращается в ApiError(%s)", async (status, kind) => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(status, { detail: "причина" }));
    const error = await catchError(createClient(fetchImpl).get("/x"));
    expect(error).toMatchObject({ kind, status, detail: "причина" });
  });

  it("не JSON в ответе 500 даёт ApiError(server) без detail", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response("<html>oops</html>", { status: 500 }));
    const error = await catchError(createClient(fetchImpl).get("/x"));
    expect(error).toMatchObject({ kind: "server", status: 500, detail: null });
  });

  it("сетевой сбой превращается в ApiError(network)", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const error = await catchError(createClient(fetchImpl).get("/x"));
    expect(error).toMatchObject({ kind: "network", status: null });
  });

  describe("таймаут", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("прерывает запрос и бросает ApiError(timeout)", async () => {
      const fetchImpl = vi.fn(
        (_url: RequestInfo | URL, init?: RequestInit) =>
          new Promise<Response>((_, reject) => {
            init?.signal?.addEventListener("abort", () =>
              reject(new DOMException("aborted", "AbortError")),
            );
          }),
      );
      const promise = catchError(
        createClient(fetchImpl as typeof fetch, { timeoutMs: 1000 }).get("/x"),
      );
      await vi.advanceTimersByTimeAsync(1000);
      expect(await promise).toMatchObject({ kind: "timeout", status: null });
    });
  });

  it("отмена вызывающим не превращается в ApiError", async () => {
    const controller = new AbortController();
    const fetchImpl = vi.fn(
      (_url: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_, reject) => {
          init?.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }),
    );
    const promise = createClient(fetchImpl as typeof fetch).get("/x", {
      signal: controller.signal,
    });
    controller.abort();
    await expect(promise).rejects.toMatchObject({ name: "AbortError" });
  });

  describe("401", () => {
    it("после успешного обновления сессии повторяет запрос один раз", async () => {
      const fetchImpl = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(401, { detail: "истёк" }))
        .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
      const onUnauthorized = vi.fn().mockResolvedValue(true);

      const result = await createClient(fetchImpl, { onUnauthorized }).get("/me");

      expect(result).toEqual({ ok: true });
      expect(onUnauthorized).toHaveBeenCalledTimes(1);
      expect(fetchImpl).toHaveBeenCalledTimes(2);
    });

    it("без обработчика бросает ApiError(unauthorized) без повторов", async () => {
      const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(401, { detail: "нет" }));
      const error = await catchError(createClient(fetchImpl).get("/me"));
      expect(error.kind).toBe("unauthorized");
      expect(fetchImpl).toHaveBeenCalledTimes(1);
    });

    it("если обновление не удалось, бросает ApiError(unauthorized)", async () => {
      const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(401, {}));
      const onUnauthorized = vi.fn().mockResolvedValue(false);
      const error = await catchError(createClient(fetchImpl, { onUnauthorized }).get("/me"));
      expect(error.kind).toBe("unauthorized");
      expect(fetchImpl).toHaveBeenCalledTimes(1);
    });

    it("не зацикливается при повторном 401", async () => {
      const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(401, {}));
      const onUnauthorized = vi.fn().mockResolvedValue(true);
      const error = await catchError(createClient(fetchImpl, { onUnauthorized }).get("/me"));
      expect(error.kind).toBe("unauthorized");
      expect(fetchImpl).toHaveBeenCalledTimes(2);
      expect(onUnauthorized).toHaveBeenCalledTimes(1);
    });

    it("сбой обработчика считается неудачным обновлением", async () => {
      const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(401, {}));
      const onUnauthorized = vi.fn().mockRejectedValue(new Error("boom"));
      const error = await catchError(createClient(fetchImpl, { onUnauthorized }).get("/me"));
      expect(error.kind).toBe("unauthorized");
    });
  });
});
