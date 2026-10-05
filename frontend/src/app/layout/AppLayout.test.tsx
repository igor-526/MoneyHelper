import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

const EMPTY_PAGE = { items: [], total: 0, limit: 100, offset: 0 };
const api = () => new FakeApiClient(withSession(() => EMPTY_PAGE));

describe("адаптивный layout", () => {
  it("на телефоне: нижняя панель навигации, верхней навигации нет", async () => {
    renderApp({ apiClient: api(), mobile: true });
    expect(await screen.findByTestId("mobile-shell")).toBeInTheDocument();
    expect(screen.queryByTestId("desktop-shell")).not.toBeInTheDocument();
    expect(screen.getAllByRole("navigation", { name: "Основная навигация" })).toHaveLength(1);
  });

  it("на широком экране: верхняя навигация, нижней панели нет", async () => {
    renderApp({ apiClient: api(), mobile: false });
    expect(await screen.findByTestId("desktop-shell")).toBeInTheDocument();
    expect(screen.queryByTestId("mobile-shell")).not.toBeInTheDocument();
  });

  it("нижняя панель содержит не более 5 пунктов", async () => {
    const { navItems } = await import("../navItems");
    expect(navItems.length).toBeLessThanOrEqual(5);
  });

  it("навигация: «Операции», «Кошельки», «Аналитика», «Настройки», без «Главная»", async () => {
    const { navItems } = await import("../navItems");
    expect(navItems.map((item) => item.label)).toEqual([
      "Операции",
      "Кошельки",
      "Аналитика",
      "Настройки",
    ]);
  });

  it.each([
    ["на телефоне", true],
    ["на широком экране", false],
  ])("%s в навигации нет пункта «Главная»", async (_name, mobile) => {
    renderApp({ apiClient: api(), mobile });
    await screen.findByTestId(mobile ? "mobile-shell" : "desktop-shell");
    expect(screen.queryByText("Главная")).not.toBeInTheDocument();
    for (const label of ["Кошельки", "Операции", "Аналитика", "Настройки"]) {
      expect(screen.getByRole("link", { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

  it("пункт «Операции» расположен перед «Кошельки»", async () => {
    const { navItems } = await import("../navItems");
    const labels = navItems.map((item) => item.label);
    expect(labels.indexOf("Операции")).toBe(labels.indexOf("Кошельки") - 1);
  });

  it("контент на телефоне лежит в main, отдельном от фиксированной панели", async () => {
    renderApp({ apiClient: api(), mobile: true });
    const main = await screen.findByRole("main");
    expect(main).toBeInTheDocument();
    expect(main).not.toContainElement(screen.getByRole("navigation"));
  });

  it("пункт «Операции» активен на /transactions", async () => {
    const { activeNavKey } = await import("../navItems");
    expect(activeNavKey("/transactions")).toBe("transactions");
  });

  it("переход на /transactions рендерит раздел операций", async () => {
    renderApp({ apiClient: api(), path: "/transactions" });
    expect(await screen.findByRole("heading", { name: "Операции" })).toBeInTheDocument();
  });

  it("отдельный пункт навигации, ведущий на /transfers, отсутствует", async () => {
    const { navItems } = await import("../navItems");
    expect(navItems.some((item) => item.path === "/transfers")).toBe(false);
  });

  it("переход на /transfers открывает вкладку «Перевод» страницы «Операции»", async () => {
    renderApp({ apiClient: api(), path: "/transfers" });
    expect(await screen.findByRole("heading", { name: "Операции" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Перевод" })).toHaveAttribute("aria-selected", "true");
  });

  it("пункт «Аналитика» расположен между «Кошельки» и «Настройки», «Настройки» остаётся последним", async () => {
    const { navItems } = await import("../navItems");
    const labels = navItems.map((item) => item.label);
    expect(labels.indexOf("Аналитика")).toBe(labels.indexOf("Кошельки") + 1);
    expect(labels.indexOf("Настройки")).toBe(labels.indexOf("Аналитика") + 1);
    expect(labels.at(-1)).toBe("Настройки");
  });

  it("пункт «Аналитика» активен на /analytics", async () => {
    const { activeNavKey } = await import("../navItems");
    expect(activeNavKey("/analytics")).toBe("analytics");
  });

  it("переход на /analytics рендерит раздел аналитики", async () => {
    renderApp({ apiClient: api(), path: "/analytics" });
    expect(await screen.findByRole("heading", { name: "Аналитика" })).toBeInTheDocument();
  });
});
