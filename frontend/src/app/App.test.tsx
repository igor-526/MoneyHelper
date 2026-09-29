import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

// Запрос на чтение при сбое сети/сервера повторяется один раз (задержка 1 с), поэтому ожидаем дольше
const RETRY_WAIT = { timeout: 4000 };

const healthy = () => new FakeApiClient(withSession(() => ({ status: "ok" })));
const failing = (error: ApiError) =>
  new FakeApiClient(
    withSession((request) => {
      if (request.path === "/health") throw error;
      return {};
    }),
  );

describe("страница-заглушка и проверка backend", () => {
  it("backend доступен", async () => {
    const api = healthy();
    renderApp({ apiClient: api });
    expect(await screen.findByText("Backend доступен")).toBeInTheDocument();
    expect(api.requests.some((r) => r.method === "GET" && r.path === "/health")).toBe(true);
  });

  it("сетевой сбой: страница показывает «недоступен» и показывается toast", async () => {
    renderApp({ apiClient: failing(new ApiError({ kind: "network", status: null })) });
    expect(
      await screen.findByText("Backend недоступен", undefined, RETRY_WAIT),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Нет соединения с сервером", undefined, RETRY_WAIT),
    ).toBeInTheDocument();
  });

  it("ответ 500: «недоступен» и toast об ошибке сервера", async () => {
    renderApp({ apiClient: failing(new ApiError({ kind: "server", status: 500 })) });
    expect(
      await screen.findByText("Backend недоступен", undefined, RETRY_WAIT),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Ошибка сервера, попробуйте позже", undefined, RETRY_WAIT),
    ).toBeInTheDocument();
  });

  it("кнопка «Повторить» повторяет запрос", async () => {
    let fail = true;
    const api = new FakeApiClient(
      withSession((request) => {
        if (request.path === "/health") {
          if (fail) throw new ApiError({ kind: "network", status: null });
          return { status: "ok" };
        }
        return {};
      }),
    );
    renderApp({ apiClient: api });
    await screen.findByText("Backend недоступен", undefined, RETRY_WAIT);

    fail = false;
    await userEvent.click(screen.getByRole("button", { name: /Повторить/ }));
    expect(await screen.findByText("Backend доступен")).toBeInTheDocument();
  });
});

describe("маршруты", () => {
  it("неизвестный маршрут показывает «Страница не найдена»", async () => {
    renderApp({ apiClient: healthy(), path: "/no/such/page" });
    expect(await screen.findByText("Страница не найдена")).toBeInTheDocument();
  });

  it("страница настроек открывается по /settings", async () => {
    renderApp({ apiClient: healthy(), path: "/settings" });
    expect(await screen.findByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("навигация переключает страницы", async () => {
    renderApp({ apiClient: healthy() });
    const nav = await screen.findByRole("navigation", { name: "Основная навигация" });
    await userEvent.click(within(nav).getByRole("link", { name: /Настройки/ }));
    expect(await screen.findByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("без сессии защищённый маршрут ведёт на /login", async () => {
    renderApp({ apiClient: new FakeApiClient(withSession(() => ({}), null)), path: "/settings" });
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("с активной сессией /login ведёт на главную", async () => {
    renderApp({ apiClient: healthy(), path: "/login" });
    expect(await screen.findByText("Backend доступен")).toBeInTheDocument();
  });
});

describe("тема на странице настроек", () => {
  it("переключатель применяет и сохраняет тёмную тему", async () => {
    renderApp({ apiClient: healthy(), path: "/settings" });
    await userEvent.click(await screen.findByText("Тёмная"));
    await waitFor(() => expect(document.documentElement).toHaveAttribute("data-theme", "dark"));
    expect(window.localStorage.getItem("moneyhelper.theme")).toBe("dark");
  });
});
