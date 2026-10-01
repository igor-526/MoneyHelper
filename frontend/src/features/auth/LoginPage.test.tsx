import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { AUTHENTICATED_USER, DEFAULT_WORKSPACE } from "@/test/session";

const WORKSPACES_PAGE = { items: [DEFAULT_WORKSPACE], total: 1, limit: 100, offset: 0 };

async function fillAndSubmit(email: string, password: string) {
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Пароль"), password);
  await userEvent.click(screen.getByRole("button", { name: "Войти" }));
}

describe("LoginPage", () => {
  it("успешный вход переводит на путь, к которому шёл пользователь", async () => {
    const api = new FakeApiClient((request) => {
      if (request.path === "/api/auth/me")
        throw new ApiError({ kind: "unauthorized", status: 401 });
      if (request.path === "/api/auth/login") return AUTHENTICATED_USER;
      if (request.path === "/api/workspaces") return WORKSPACES_PAGE;
      return { status: "ok" };
    });

    renderApp({ apiClient: api, path: "/settings" });
    await screen.findByRole("heading", { name: "Вход" });

    await fillAndSubmit("user@example.com", "correct-horse-battery");

    expect(await screen.findByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("неверные данные показывают сообщение у формы, а не toast, и очищают пароль", async () => {
    const api = new FakeApiClient((request) => {
      if (request.path === "/api/auth/me")
        throw new ApiError({ kind: "unauthorized", status: 401 });
      if (request.path === "/api/auth/login") {
        throw new ApiError({
          kind: "unauthorized",
          status: 401,
          detail: "Неверный email или пароль",
        });
      }
      return { status: "ok" };
    });

    renderApp({ apiClient: api, path: "/login" });
    await screen.findByRole("heading", { name: "Вход" });

    await fillAndSubmit("user@example.com", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent("Неверный email или пароль");
    expect(screen.queryByText("Сессия истекла, войдите снова")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Пароль")).toHaveValue("");
  });

  it("сетевой сбой показывает toast, а не сообщение у формы", async () => {
    const api = new FakeApiClient((request) => {
      if (request.path === "/api/auth/me")
        throw new ApiError({ kind: "unauthorized", status: 401 });
      if (request.path === "/api/auth/login") throw new ApiError({ kind: "network", status: null });
      return { status: "ok" };
    });

    renderApp({ apiClient: api, path: "/login" });
    await screen.findByRole("heading", { name: "Вход" });

    await fillAndSubmit("user@example.com", "correct-horse-battery");

    expect(await screen.findByText("Нет соединения с сервером")).toBeInTheDocument();
  });
});
