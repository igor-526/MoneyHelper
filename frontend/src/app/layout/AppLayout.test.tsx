import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";

const api = () => new FakeApiClient(() => ({ status: "ok" }));

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

  it("контент на телефоне лежит в main, отдельном от фиксированной панели", async () => {
    renderApp({ apiClient: api(), mobile: true });
    const main = await screen.findByRole("main");
    expect(main).toBeInTheDocument();
    expect(main).not.toContainElement(screen.getByRole("navigation"));
  });
});
