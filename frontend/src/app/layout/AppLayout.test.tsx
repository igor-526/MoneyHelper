import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { withSession } from "@/test/session";

const api = () => new FakeApiClient(withSession(() => ({ status: "ok" })));

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

  it("пункт «Операции» расположен между «Кошельки» и «Настройки»", async () => {
    const { navItems } = await import("../navItems");
    const labels = navItems.map((item) => item.label);
    expect(labels.indexOf("Операции")).toBe(labels.indexOf("Кошельки") + 1);
    expect(labels.indexOf("Настройки")).toBe(labels.indexOf("Операции") + 1);
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
});
