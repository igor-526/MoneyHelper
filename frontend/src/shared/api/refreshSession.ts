export type RefreshSession = () => Promise<boolean>;

/**
 * Single-flight обновление сессии: `POST /api/auth/refresh` с cookies. Несколько запросов, столкнувшихся
 * с 401 одновременно, дожидаются одного и того же вызова, а не создают по обновлению каждый.
 * Сетевой сбой и любой не-2xx ответ дают `false`, без исключений — решение, что делать дальше, остаётся
 * за вызывающей стороной (`FetchApiClient`).
 */
export function createSingleFlightRefresh(
  baseUrl: string,
  fetchImpl: typeof fetch = fetch,
): RefreshSession {
  let pending: Promise<boolean> | null = null;

  return () => {
    pending ??= fetchImpl(`${baseUrl}/api/auth/refresh`, { method: "POST", credentials: "include" })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        pending = null;
      });
    return pending;
  };
}
