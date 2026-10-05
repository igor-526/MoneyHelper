import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FakeApiClient } from "@/test/FakeApiClient";
import { renderApp } from "@/test/renderApp";
import { DEFAULT_WORKSPACE, withSession } from "@/test/session";

const EMPTY_PAGE = { items: [], total: 0, limit: 100, offset: 0 };
const CURRENCIES_PAGE = {
  items: [
    { id: DEFAULT_WORKSPACE.currency_id, code: "RUB", name: "Российский рубль", decimal_places: 2 },
  ],
  total: 1,
  limit: 100,
  offset: 0,
};
const api = () =>
  new FakeApiClient(
    withSession((request) => (request.path === "/api/currencies" ? CURRENCIES_PAGE : EMPTY_PAGE)),
  );

describe("индикатор текущего воркспейса", () => {
  it.each([
    ["на телефоне", true, "mobile-shell"],
    ["на широком экране", false, "desktop-shell"],
  ])("%s показывает название и код валюты", async (_name, mobile, shell) => {
    renderApp({ apiClient: api(), mobile });

    const badge = await screen.findByRole("link", {
      name: `Текущий воркспейс: ${DEFAULT_WORKSPACE.name}`,
    });
    expect(screen.getByTestId(shell)).toContainElement(badge);
    expect(await screen.findByText("RUB")).toBeInTheDocument();
  });

  it("ведёт в «Настройки» с секцией воркспейсов", async () => {
    renderApp({ apiClient: api(), path: "/wallets" });

    await userEvent.click(await screen.findByRole("link", { name: /Текущий воркспейс/ }));

    expect(await screen.findByRole("heading", { name: "Настройки" })).toBeInTheDocument();
    expect(screen.getByText("Воркспейсы")).toBeInTheDocument();
  });
});
