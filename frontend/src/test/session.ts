import type { User } from "@/features/auth/session";
import type { Workspace } from "@/features/workspaces/Workspace";
import { ApiError } from "@/shared/api";
import type { FakeHandler } from "./FakeApiClient";

export const AUTHENTICATED_USER: User = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "user@example.com",
  created_at: "2026-01-01T00:00:00Z",
};

/**
 * Единственный воркспейс по умолчанию — `RequireWorkspace` выбирает его автоматически (без сохранённого id
 * выбор среди одного варианта не нужен), поэтому маршрутные тесты проходят `RequireWorkspace` без лишнего клика.
 */
export const DEFAULT_WORKSPACE: Workspace = {
  id: "22222222-2222-2222-2222-222222222222",
  name: "Тестовый воркспейс",
  currency_id: "33333333-3333-3333-3333-333333333333",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

/**
 * Оборачивает обработчик `FakeApiClient`: `GET /api/auth/me` отвечает готовой сессией (или 401), `GET
 * /api/workspaces` — списком из одного воркспейса (`RequireWorkspace` выбирает его сам), остальные запросы
 * уходят в исходный обработчик. Нужен почти всем тестам оболочки — маршруты, кроме `/login` и `/register`,
 * требуют сессию и воркспейс.
 */
export function withSession(
  handler: FakeHandler,
  user: User | null = AUTHENTICATED_USER,
): FakeHandler {
  return (request) => {
    if (request.path === "/api/auth/me") {
      if (user === null) throw new ApiError({ kind: "unauthorized", status: 401 });
      return user;
    }
    if (request.path === "/api/workspaces" && request.method === "GET") {
      return { items: [DEFAULT_WORKSPACE], total: 1, limit: 100, offset: 0 };
    }
    return handler(request);
  };
}
