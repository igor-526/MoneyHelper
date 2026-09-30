import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { DEFAULT_PAGE_SIZE } from "./useTransfers";
import { TransfersPage } from "./TransfersPage";

const WALLETS = [
  {
    id: "w1",
    name: "Наличные",
    icon: "wallet",
    currency_ids: ["cur1", "cur2"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "w2",
    name: "Карта",
    icon: "credit-card",
    currency_ids: ["cur1", "cur2"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
];

const CURRENCIES = [
  { id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 },
  { id: "cur2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
];

const TRANSFERS = [
  {
    id: "t1",
    from_wallet_id: "w1",
    to_wallet_id: "w2",
    currency_id: "cur1",
    amount: "10.00",
    occurred_at: "2026-03-01T12:00:00Z",
    created_at: "2026-03-01T12:00:00Z",
    updated_at: null,
  },
];

function page(
  items: unknown[],
  overrides: Partial<{ total: number; limit: number; offset: number }> = {},
) {
  return {
    items,
    total: overrides.total ?? items.length,
    limit: overrides.limit ?? DEFAULT_PAGE_SIZE,
    offset: overrides.offset ?? 0,
  };
}

function defaultTransfersHandler(overrides: Partial<{ total: number }> = {}): FakeHandler {
  return () => page(TRANSFERS, overrides);
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/wallets") return page(WALLETS, { limit: 100 });
    if (request.path === "/api/currencies") return page(CURRENCIES, { limit: 100 });
    return handler(request);
  };
}

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(withFixtures(handler));
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <ToastProvider>{children}</ToastProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, toast, wrapper };
}

function transfersRequests(api: FakeApiClient) {
  return api.requests.filter((r) => r.path === "/api/transfers");
}

async function chooseFromDropdown(combobox: HTMLElement, optionLabel: string) {
  await userEvent.click(combobox);
  const dropdown = await waitFor(() => {
    const nodes = document.querySelectorAll(".ant-select-dropdown-list");
    if (nodes.length === 0) throw new Error("Выпадающий список ещё не отрисован");
    return nodes[nodes.length - 1] as HTMLElement;
  });
  await userEvent.click(within(dropdown).getByText(optionLabel));
}

async function chooseOption(comboboxName: string, optionLabel: string) {
  await chooseFromDropdown(screen.getByRole("combobox", { name: comboboxName }), optionLabel);
}

async function fillFormOption(labelText: string, optionLabel: string) {
  const label = screen.getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  await chooseFromDropdown(within(formItem).getByRole("combobox"), optionLabel);
}

async function goToPage(pageNumber: number) {
  await userEvent.click(screen.getByTitle(String(pageNumber)));
}

describe("TransfersPage", () => {
  it("загрузка и рендер списка карточек", async () => {
    const { wrapper } = setup(defaultTransfersHandler());
    render(<TransfersPage />, { wrapper });

    expect(await screen.findByText("Наличные → Карта")).toBeInTheDocument();
    expect(screen.getByText("10.00 USD")).toBeInTheDocument();
  });

  it("пустой список показывает EmptyState, кнопка действия открывает форму создания", async () => {
    const { wrapper } = setup(() => page([]));
    render(<TransfersPage />, { wrapper });

    expect(await screen.findByText("Переводов пока нет")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Создать перевод" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("фильтр по кошельку передаёт wallet_id и сбрасывает страницу на 1", async () => {
    const { api, wrapper } = setup(defaultTransfersHandler({ total: 40 }));
    render(<TransfersPage />, { wrapper });
    await screen.findByText("Наличные → Карта");

    await goToPage(2);
    await waitFor(() =>
      expect(transfersRequests(api).at(-1)).toMatchObject({ query: { offset: DEFAULT_PAGE_SIZE } }),
    );

    await chooseOption("Кошелёк", "Наличные");

    await waitFor(() =>
      expect(transfersRequests(api).at(-1)).toMatchObject({
        query: { wallet_id: "w1", offset: 0 },
      }),
    );
  });

  it("фильтр по диапазону дат передаёт date_from/date_to", async () => {
    const { api, wrapper } = setup(defaultTransfersHandler());
    render(<TransfersPage />, { wrapper });
    await screen.findByText("Наличные → Карта");

    await userEvent.type(screen.getByPlaceholderText("Дата от"), "2026-03-01");
    await userEvent.keyboard("{Enter}");
    await userEvent.type(screen.getByPlaceholderText("Дата до"), "2026-03-10");
    await userEvent.keyboard("{Enter}");

    await waitFor(() =>
      expect(transfersRequests(api).at(-1)).toMatchObject({
        query: {
          date_from: dayjs("2026-03-01").startOf("day").toISOString(),
          date_to: dayjs("2026-03-10").endOf("day").toISOString(),
        },
      }),
    );
  });

  it("переключение страницы запрашивает нужный offset", async () => {
    const { api, wrapper } = setup(defaultTransfersHandler({ total: 40 }));
    render(<TransfersPage />, { wrapper });
    await screen.findByText("Наличные → Карта");

    await goToPage(2);

    await waitFor(() =>
      expect(transfersRequests(api).at(-1)).toMatchObject({
        query: { offset: DEFAULT_PAGE_SIZE, limit: DEFAULT_PAGE_SIZE },
      }),
    );
  });

  it("кнопка «Редактировать» карточки открывает форму с ожидаемыми пропами", async () => {
    const { wrapper } = setup(defaultTransfersHandler());
    render(<TransfersPage />, { wrapper });
    await screen.findByText("Наличные → Карта");

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));

    expect(await screen.findByText("Редактировать перевод")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Сумма")).toHaveValue("10.00"));
  });

  it("ошибка загрузки показывает toast (общий обработчик)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });
    render(<TransfersPage />, { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });

  it("сквозной сценарий: создание убирает EmptyState, редактирование обновляет карточку, удаление возвращает к EmptyState", async () => {
    let items: unknown[] = [];
    const handler: FakeHandler = (request) => {
      if (request.path === "/api/transfers" && request.method === "GET") return page(items);
      if (request.path === "/api/transfers" && request.method === "POST") {
        const body = request.body as {
          from_wallet_id: string;
          to_wallet_id: string;
          currency_id: string;
          amount: string;
        };
        const created = {
          id: "new1",
          ...body,
          occurred_at: "2026-03-15T00:00:00Z",
          created_at: "2026-03-15T00:00:00Z",
          updated_at: null,
        };
        items = [created];
        return created;
      }
      if (request.path === "/api/transfers/new1" && request.method === "PUT") {
        const body = request.body as { amount: string };
        const updated = { ...(items[0] as Record<string, unknown>), amount: body.amount };
        items = [updated];
        return updated;
      }
      if (request.path === "/api/transfers/new1" && request.method === "DELETE") {
        items = [];
        return undefined;
      }
      return page(items);
    };
    const { wrapper } = setup(handler);
    render(<TransfersPage />, { wrapper });

    expect(await screen.findByText("Переводов пока нет")).toBeInTheDocument();

    // создание
    await userEvent.click(screen.getByRole("button", { name: "Создать перевод" }));
    await fillFormOption("Откуда", "Наличные");
    await fillFormOption("Куда", "Карта");
    await fillFormOption("Валюта", "USD — Доллар США");
    let dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Сумма"), "10");
    await userEvent.click(within(dialog).getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("10 USD")).toBeInTheDocument();
    expect(screen.queryByText("Переводов пока нет")).not.toBeInTheDocument();

    // редактирование
    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    dialog = await screen.findByRole("dialog");
    await userEvent.clear(within(dialog).getByLabelText("Сумма"));
    await userEvent.type(within(dialog).getByLabelText("Сумма"), "20");
    await userEvent.click(within(dialog).getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("20 USD")).toBeInTheDocument();

    // удаление
    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    expect(await screen.findByText("Переводов пока нет")).toBeInTheDocument();
  });
});
