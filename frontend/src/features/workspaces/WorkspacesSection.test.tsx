import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { WorkspaceActionsContext } from "./WorkspaceActionsContext";
import { WorkspaceContext } from "./WorkspaceContext";
import { WorkspacesSection } from "./WorkspacesSection";

const WORKSPACES_PAGE = {
  items: [
    {
      id: "1",
      name: "Личное",
      currency_id: "c1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "2",
      name: "Поездка в Китай",
      currency_id: "c2",
      created_at: "2026-01-02T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

const CURRENCIES_PAGE = {
  items: [
    { id: "c1", code: "RUB", name: "Российский рубль", decimal_places: 2 },
    { id: "c2", code: "CNY", name: "Юань", decimal_places: 2 },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

const handle =
  (workspaces: unknown): FakeHandler =>
  (request) =>
    request.path === "/api/currencies" ? CURRENCIES_PAGE : workspaces;

function setup(handler: FakeHandler, switchWorkspace: (id: string) => void = vi.fn()) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <WorkspaceContext.Provider value="1">
          <WorkspaceActionsContext.Provider value={{ switchWorkspace }}>
            <ToastProvider>{children}</ToastProvider>
          </WorkspaceActionsContext.Provider>
        </WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("WorkspacesSection", () => {
  it("текущий воркспейс помечен тегом и без кнопки «Переключить»", async () => {
    const { wrapper } = setup(handle(WORKSPACES_PAGE));
    render(<WorkspacesSection />, { wrapper });

    await screen.findByText("Личное");
    const currentRow = screen.getByText("Личное").closest("div.ant-flex") as HTMLElement;
    expect(within(currentRow).getByText("текущий")).toBeInTheDocument();
    expect(
      within(currentRow).queryByRole("button", { name: "Переключить" }),
    ).not.toBeInTheDocument();
  });

  it("у каждого воркспейса показан код его валюты", async () => {
    const { wrapper } = setup(handle(WORKSPACES_PAGE));
    render(<WorkspacesSection />, { wrapper });

    await screen.findByText("Личное");
    const first = screen.getByText("Личное").closest("div.ant-flex") as HTMLElement;
    const second = screen.getByText("Поездка в Китай").closest("div.ant-flex") as HTMLElement;
    expect(await within(first).findByText("RUB")).toBeInTheDocument();
    expect(await within(second).findByText("CNY")).toBeInTheDocument();
  });

  it("кнопка «Переключить» у не текущего воркспейса вызывает switchWorkspace", async () => {
    const switchWorkspace = vi.fn();
    const { wrapper } = setup(handle(WORKSPACES_PAGE), switchWorkspace);
    render(<WorkspacesSection />, { wrapper });

    await screen.findByText("Поездка в Китай");
    const row = screen.getByText("Поездка в Китай").closest("div.ant-flex") as HTMLElement;
    await userEvent.click(within(row).getByRole("button", { name: "Переключить" }));

    expect(switchWorkspace).toHaveBeenCalledWith("2");
  });

  it("«Создать воркспейс» открывает форму создания", async () => {
    const { wrapper } = setup(handle(WORKSPACES_PAGE));
    render(<WorkspacesSection />, { wrapper });
    await screen.findByText("Личное");

    await userEvent.click(screen.getByRole("button", { name: "Создать воркспейс" }));

    expect(await screen.findByLabelText("Название")).toHaveValue("");
  });

  it("«Переименовать» открывает форму с предзаполненным названием", async () => {
    const { wrapper } = setup(handle(WORKSPACES_PAGE));
    render(<WorkspacesSection />, { wrapper });
    await screen.findByText("Личное");

    const row = screen.getByText("Личное").closest("div.ant-flex") as HTMLElement;
    await userEvent.click(within(row).getByRole("button", { name: "Переименовать" }));

    expect(await screen.findByLabelText("Название")).toHaveValue("Личное");
  });

  it("подтверждение в Popconfirm вызывает DELETE /api/workspaces/{id}", async () => {
    const { api, wrapper } = setup(handle(WORKSPACES_PAGE));
    render(<WorkspacesSection />, { wrapper });
    await screen.findByText("Поездка в Китай");

    const row = screen.getByText("Поездка в Китай").closest("div.ant-flex") as HTMLElement;
    await userEvent.click(within(row).getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some((r) => r.method === "DELETE" && r.path === "/api/workspaces/2"),
      ).toBe(true),
    );
  });
});
