import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { AUTHENTICATED_USER, withSession } from "@/test/session";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("RequireAuth", () => {
  it("показывает спиннер, пока сессия проверяется, и контент после её подтверждения", async () => {
    const { promise, resolve } = deferred<typeof AUTHENTICATED_USER>();
    const api = new FakeApiClient((request) =>
      request.path === "/api/auth/me" ? promise : { status: "ok" },
    );

    renderApp({ apiClient: api, path: "/" });

    expect(screen.queryByText("Backend доступен")).not.toBeInTheDocument();
    resolve(AUTHENTICATED_USER);

    expect(await screen.findByText("Backend доступен")).toBeInTheDocument();
  });

  it("без сессии перенаправляет на /login и сохраняет исходный путь", async () => {
    const api = new FakeApiClient(withSession(() => ({}), null));

    renderApp({ apiClient: api, path: "/settings" });

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("без сессии переход на /transactions перенаправляет на /login", async () => {
    const api = new FakeApiClient(withSession(() => ({}), null));

    renderApp({ apiClient: api, path: "/transactions" });

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });
});

describe("GuestOnly", () => {
  it("с активной сессией /register тоже ведёт на главную", async () => {
    const api = new FakeApiClient(withSession(() => ({ status: "ok" })));

    renderApp({ apiClient: api, path: "/register" });

    expect(await screen.findByText("Backend доступен")).toBeInTheDocument();
  });

  it("без сессии /register показывает форму регистрации", async () => {
    const api = new FakeApiClient(withSession(() => ({}), null));

    renderApp({ apiClient: api, path: "/register" });

    expect(await screen.findByRole("heading", { name: "Регистрация" })).toBeInTheDocument();
  });
});
