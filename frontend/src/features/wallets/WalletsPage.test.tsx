import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { WalletsPage } from "./WalletsPage";

const TEST_WORKSPACE_ID = "workspace-1";

const CURRENCIES_PAGE = {
  items: [
    { id: "1", code: "USD", name: "Доллар США", decimal_places: 2 },
    { id: "2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

function walletsPage(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

const WALLETS = [
  {
    id: "1",
    name: "Наличные",
    icon: "wallet",
    currency_ids: ["1", "2"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "2",
    name: "Карта",
    icon: "credit-card",
    currency_ids: ["1"],
    created_at: "2026-01-02T00:00:00Z",
    updated_at: null,
  },
];

function setup(handler: FakeHandler) {
  const api = new FakeApiClient((request) => {
    if (request.path === "/api/currencies") return CURRENCIES_PAGE;
    return handler(request);
  });
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>
          <ToastProvider>{children}</ToastProvider>
        </WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, toast, wrapper };
}

describe("WalletsPage", () => {
  it("загрузка и рендер списка карточек с чипами валют", async () => {
    const { wrapper } = setup(() => walletsPage(WALLETS));
    render(<WalletsPage />, { wrapper });

    expect(await screen.findByText("Наличные")).toBeInTheDocument();
    expect(screen.getByText("Карта")).toBeInTheDocument();
    expect(screen.getAllByText("USD")).toHaveLength(2);
    expect(screen.getAllByText("RUB")).toHaveLength(1);
  });

  it("пустой список показывает EmptyState, кнопка действия открывает форму создания", async () => {
    const { wrapper } = setup(() => walletsPage([]));
    render(<WalletsPage />, { wrapper });

    expect(await screen.findByText("Кошельков пока нет")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Создать кошелёк" }));

    expect(await screen.findByLabelText("Название")).toHaveValue("");
  });

  it("кнопка «Создать кошелёк» и «Редактировать» карточки открывают форму с ожидаемыми пропами", async () => {
    const { wrapper } = setup(() => walletsPage(WALLETS));
    render(<WalletsPage />, { wrapper });
    await screen.findByText("Наличные");

    await userEvent.click(screen.getByRole("button", { name: "Создать кошелёк" }));
    expect(await screen.findByLabelText("Название")).toHaveValue("");
    // Закрываем, чтобы не открыть форму поверх формы.
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const [editButton] = screen.getAllByRole("button", { name: "Редактировать" });
    await userEvent.click(editButton as HTMLElement);
    expect(await screen.findByLabelText("Название")).toHaveValue("Наличные");
  });

  it("ошибка загрузки показывает toast (общий обработчик)", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });
    render(<WalletsPage />, { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });
});
