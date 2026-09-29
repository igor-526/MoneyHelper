import { describe, expect, it, vi } from "vitest";
import { createSingleFlightRefresh } from "./refreshSession";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

describe("createSingleFlightRefresh", () => {
  it("вызывает POST /api/auth/refresh с cookies и возвращает true при 2xx", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    const refresh = createSingleFlightRefresh("http://api.test", fetchImpl);

    await expect(refresh()).resolves.toBe(true);
    expect(fetchImpl).toHaveBeenCalledWith("http://api.test/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
  });

  it("параллельные вызовы дожидаются одного обновления (single-flight)", async () => {
    const { promise, resolve } = deferred<Response>();
    const fetchImpl = vi.fn().mockReturnValue(promise);
    const refresh = createSingleFlightRefresh("http://api.test", fetchImpl);

    const first = refresh();
    const second = refresh();
    resolve(new Response(null, { status: 204 }));

    expect(await first).toBe(true);
    expect(await second).toBe(true);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("после завершения следующий вызов запускает новое обновление", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    const refresh = createSingleFlightRefresh("http://api.test", fetchImpl);

    await refresh();
    await refresh();

    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("не-2xx ответ даёт false", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 401 }));
    const refresh = createSingleFlightRefresh("http://api.test", fetchImpl);

    await expect(refresh()).resolves.toBe(false);
  });

  it("сетевой сбой даёт false без исключения", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const refresh = createSingleFlightRefresh("http://api.test", fetchImpl);

    await expect(refresh()).resolves.toBe(false);
  });
});
