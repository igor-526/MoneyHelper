import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

const EMPTY_PAGE = { items: [], total: 0, limit: 100, offset: 0 };
const withWallets: FakeHandler = (request) => {
  if (
    request.path === "/api/wallets" ||
    request.path === "/api/currencies" ||
    request.path === "/api/categories"
  )
    return EMPTY_PAGE;
  return { status: "ok" };
};
const authedApi = () => new FakeApiClient(withSession(withWallets));

describe("маршруты", () => {
  it("неизвестный маршрут показывает «Страница не найдена»", async () => {
    renderApp({ apiClient: authedApi(), path: "/no/such/page" });
    expect(await screen.findByText("Страница не найдена")).toBeInTheDocument();
  });

  it("страница настроек открывается по /settings", async () => {
    renderApp({ apiClient: authedApi(), path: "/settings" });
    expect(await screen.findByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("блок «Категории» на странице настроек виден и ссылка ведёт на /categories", async () => {
    renderApp({
      apiClient: new FakeApiClient(withSession(withWallets)),
      path: "/settings",
    });
    await screen.findByRole("heading", { name: "Настройки" });

    await userEvent.click(screen.getByRole("link", { name: "Открыть" }));

    expect(await screen.findByRole("heading", { name: "Категории" })).toBeInTheDocument();
  });

  it("навигация переключает страницы", async () => {
    renderApp({ apiClient: authedApi() });
    const nav = await screen.findByRole("navigation", { name: "Основная навигация" });
    await userEvent.click(within(nav).getByRole("link", { name: /Настройки/ }));
    expect(await screen.findByRole("heading", { name: "Настройки" })).toBeInTheDocument();
  });

  it("пункт «Кошельки» виден авторизованному пользователю и ведёт на /wallets", async () => {
    renderApp({ apiClient: new FakeApiClient(withSession(withWallets)) });
    const nav = await screen.findByRole("navigation", { name: "Основная навигация" });
    await userEvent.click(within(nav).getByRole("link", { name: /Кошельки/ }));
    expect(await screen.findByText("Кошельков пока нет")).toBeInTheDocument();
  });

  it("без сессии защищённый маршрут ведёт на /login", async () => {
    renderApp({ apiClient: new FakeApiClient(withSession(() => ({}), null)), path: "/settings" });
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("без сессии прямой переход на /wallets ведёт на /login", async () => {
    renderApp({ apiClient: new FakeApiClient(withSession(() => ({}), null)), path: "/wallets" });
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("без сессии прямой переход на /categories ведёт на /login", async () => {
    renderApp({
      apiClient: new FakeApiClient(withSession(() => ({}), null)),
      path: "/categories",
    });
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("без сессии прямой переход на /transfers ведёт на /login", async () => {
    renderApp({ apiClient: new FakeApiClient(withSession(() => ({}), null)), path: "/transfers" });
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("с активной сессией /login ведёт на «Кошельки»", async () => {
    const { router } = renderApp({ apiClient: authedApi(), path: "/login" });
    expect(await screen.findByText("Кошельков пока нет")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/wallets");
  });

  it("корневой маршрут / ведёт на «Кошельки»", async () => {
    const { router } = renderApp({ apiClient: authedApi(), path: "/" });
    expect(await screen.findByText("Кошельков пока нет")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/wallets");
  });

  it("приложение не обращается к /health и не показывает статус backend", async () => {
    const api = authedApi();
    renderApp({ apiClient: api });
    await screen.findByText("Кошельков пока нет");
    expect(api.requests.some((r) => r.path === "/health")).toBe(false);
    expect(screen.queryByText(/Backend/)).not.toBeInTheDocument();
  });

  it("управление воркспейсами доступно в «Настройках»", async () => {
    renderApp({ apiClient: authedApi(), path: "/settings" });
    expect(await screen.findByRole("button", { name: "Создать воркспейс" })).toBeInTheDocument();
  });
});

describe("тема на странице настроек", () => {
  it("переключатель применяет и сохраняет тёмную тему", async () => {
    renderApp({ apiClient: authedApi(), path: "/settings" });
    await userEvent.click(await screen.findByText("Тёмная"));
    await waitFor(() => expect(document.documentElement).toHaveAttribute("data-theme", "dark"));
    expect(window.localStorage.getItem("moneyhelper.theme")).toBe("dark");
  });
});
