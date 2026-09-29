import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

describe("истёкшая сессия во время работы", () => {
  it("unauthorized у обычного (не silent) запроса показывает toast и переводит на /login", async () => {
    // /api/auth/me (проверка сессии) отвечает успехом — пользователь уже на защищённой странице;
    // а вот /health (обычный, не silent запрос) внезапно отвечает unauthorized — как если бы сессия
    // истекла и обновить её не удалось (для FakeApiClient это конечное состояние, retry не делает).
    const api = new FakeApiClient(
      withSession((request) => {
        if (request.path === "/health") throw new ApiError({ kind: "unauthorized", status: 401 });
        return {};
      }),
    );

    renderApp({ apiClient: api, path: "/" });
    await screen.findByText("MoneyHelper");

    expect(await screen.findByText("Сессия истекла, войдите снова")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("silent-запрос (проверка сессии) не показывает toast «Сессия истекла»", async () => {
    const api = new FakeApiClient(withSession(() => ({}), null));

    renderApp({ apiClient: api, path: "/" });

    await screen.findByRole("heading", { name: "Вход" });
    expect(screen.queryByText("Сессия истекла, войдите снова")).not.toBeInTheDocument();
  });
});
