import type { User } from "@/features/auth/session";
import { ApiError } from "@/shared/api";
import type { FakeHandler } from "./FakeApiClient";

export const AUTHENTICATED_USER: User = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "user@example.com",
  created_at: "2026-01-01T00:00:00Z",
};

/**
 * Оборачивает обработчик `FakeApiClient`: `GET /api/auth/me` отвечает готовой сессией (или 401),
 * остальные запросы уходят в исходный обработчик. Нужен почти всем тестам оболочки — маршруты, кроме
 * `/login` и `/register`, требуют сессию.
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
    return handler(request);
  };
}
