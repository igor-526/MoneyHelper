import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { setMedia } from "@/test/matchMedia";
import type { Workspace } from "./Workspace";
import { WorkspaceForm } from "./WorkspaceForm";

const WORKSPACE: Workspace = {
  id: "5",
  name: "Личное",
  currency_id: "c1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const CURRENCIES_PAGE = {
  items: [
    { id: "c1", code: "RUB", name: "Российский рубль", decimal_places: 2 },
    { id: "c2", code: "USD", name: "Доллар США", decimal_places: 2 },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

const walletsPage = (total: number) => ({ items: [], total, limit: 1, offset: 0 });

/** Ответы справочника валют и проверки кошельков + заданный ответ на остальные запросы. */
const withLookups =
  (handler: FakeHandler, wallets = 0): FakeHandler =>
  (request) => {
    if (request.path === "/api/currencies") return CURRENCIES_PAGE;
    if (request.path.endsWith("/wallets")) return walletsPage(wallets);
    return handler(request);
  };

/** Настоящий `ToastProvider`, чтобы проверять видимые уведомления, как использует их компонент. */
function setup(handler: FakeHandler, wallets = 0) {
  const api = new FakeApiClient(withLookups(handler, wallets));
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <ToastProvider>{children}</ToastProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("WorkspaceForm", () => {
  it("создание: успех добавляет воркспейс, вызывает onSuccess и закрывает форму", async () => {
    const CREATED = {
      id: "9",
      name: "Поездка",
      currency_id: "c2",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    render(<WorkspaceForm open onClose={onClose} onSuccess={onSuccess} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Поездка");
    await userEvent.click(screen.getByLabelText("Основная валюта"));
    await userEvent.click(await screen.findByText("USD — Доллар США"));
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "POST",
      path: "/api/workspaces",
      body: { name: "Поездка", currency_id: "c2" },
    });
    expect(onSuccess).toHaveBeenCalledWith(CREATED);
    expect(await screen.findByText("Воркспейс создан")).toBeInTheDocument();
  });

  it("создание без валюты: сообщение у поля, запрос не отправляется", async () => {
    const { api, wrapper } = setup(() => WORKSPACE);
    render(<WorkspaceForm open onClose={vi.fn()} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Поездка");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Выберите валюту")).toBeInTheDocument();
    expect(api.requests.some((r) => r.method === "POST")).toBe(false);
  });

  it("переименование: поле предзаполнено, успех обновляет воркспейс", async () => {
    const UPDATED = { ...WORKSPACE, name: "Обновлённый" };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<WorkspaceForm open workspace={WORKSPACE} onClose={onClose} />, { wrapper });

    expect(screen.getByLabelText("Название")).toHaveValue("Личное");

    await userEvent.clear(screen.getByLabelText("Название"));
    await userEvent.type(screen.getByLabelText("Название"), "Обновлённый");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: "/api/workspaces/5",
      body: { name: "Обновлённый", currency_id: "c1" },
    });
    expect(await screen.findByText("Воркспейс переименован")).toBeInTheDocument();
  });

  it("редактирование воркспейса без кошельков: валюту можно менять", async () => {
    const { wrapper } = setup(() => WORKSPACE, 0);
    render(<WorkspaceForm open workspace={WORKSPACE} onClose={vi.fn()} />, { wrapper });

    await waitFor(() => expect(screen.getByLabelText("Основная валюта")).toBeEnabled());
    expect(screen.queryByText(/Валюту нельзя изменить/)).not.toBeInTheDocument();
  });

  it("редактирование воркспейса с кошельками: валюта заблокирована с пояснением", async () => {
    const { wrapper } = setup(() => WORKSPACE, 2);
    render(<WorkspaceForm open workspace={WORKSPACE} onClose={vi.fn()} />, { wrapper });

    expect(await screen.findByText(/Валюту нельзя изменить/)).toBeInTheDocument();
    expect(screen.getByLabelText("Основная валюта")).toBeDisabled();
    expect(await screen.findByText("RUB — Российский рубль")).toBeInTheDocument();
  });

  it("ошибка валидации по полю остаётся в форме и не закрывает её", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { name: ["Название не может быть пустым"] },
      });
    });
    const onClose = vi.fn();
    render(<WorkspaceForm open onClose={onClose} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "  ");
    await userEvent.click(screen.getByLabelText("Основная валюта"));
    await userEvent.click(await screen.findByText("RUB — Российский рубль"));
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Название не может быть пустым")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => WORKSPACE);
    render(<WorkspaceForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => WORKSPACE);
    render(<WorkspaceForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});
