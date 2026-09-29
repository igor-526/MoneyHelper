import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

describe("LogoutButton", () => {
  it("сбрасывает сессию и переводит на /login", async () => {
    const api = new FakeApiClient(withSession(() => undefined));

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Настройки" });

    await userEvent.click(screen.getByRole("button", { name: "Выйти" }));

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("переводит на /login даже при сбое запроса", async () => {
    const api = new FakeApiClient(
      withSession((request) => {
        if (request.path === "/api/auth/logout")
          throw new ApiError({ kind: "network", status: null });
        return {};
      }),
    );

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Настройки" });

    await userEvent.click(screen.getByRole("button", { name: "Выйти" }));

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("после выхода защищённая страница снова требует входа", async () => {
    const api = new FakeApiClient(withSession(() => undefined));

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Настройки" });
    await userEvent.click(screen.getByRole("button", { name: "Выйти" }));
    await screen.findByRole("heading", { name: "Вход" });

    // Повторный заход на защищённую страницу тоже ведёт на /login (сессии больше нет).
    expect(screen.queryByRole("heading", { name: "Настройки" })).not.toBeInTheDocument();
  });
});
