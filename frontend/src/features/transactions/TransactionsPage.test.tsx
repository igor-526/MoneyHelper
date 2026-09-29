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
import { DEFAULT_PAGE_SIZE } from "./useTransactions";
import { TransactionsPage } from "./TransactionsPage";

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
    currency_ids: ["cur2"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
];

const CURRENCIES = [
  { id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 },
  { id: "cur2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
];

const CATEGORIES = [
  {
    id: "c1",
    type: "income",
    name: "Зарплата",
    icon: "banknote",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "c2",
    type: "expense",
    name: "Продукты",
    icon: "coins",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
];

const TRANSACTIONS = [
  {
    id: "t1",
    wallet_id: "w1",
    category_id: "c1",
    legs: [{ currency_id: "cur1", amount: "10.00" }],
    occurred_at: "2026-03-01T12:00:00Z",
    created_at: "2026-03-01T12:00:00Z",
    updated_at: null,
  },
];

/** Обработчик по умолчанию: список операций + пустые балансы (когда фильтр «Кошелёк» выбран, но балансы не важны). */
function defaultTransactionsHandler(overrides: Partial<{ total: number }> = {}): FakeHandler {
  return (request) => {
    if (request.path.endsWith("/balances")) return [];
    return page(TRANSACTIONS, overrides);
  };
}

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

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/wallets") return page(WALLETS, { limit: 100 });
    if (request.path === "/api/currencies") return page(CURRENCIES, { limit: 100 });
    if (request.path === "/api/categories") {
      const type = request.query?.type as string | undefined;
      const items = type ? CATEGORIES.filter((c) => c.type === type) : CATEGORIES;
      return page(items, { limit: 100 });
    }
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

function transactionsRequests(api: FakeApiClient) {
  return api.requests.filter((r) => r.path === "/api/transactions");
}

/**
 * Опция ищется внутри видимого списка выпадающего меню (`.ant-select-dropdown-list`), а не по всему документу —
 * иначе текст совпадает с одноимённым текстом карточек операций (например, названием кошелька/категории).
 */
async function chooseFromDropdown(combobox: HTMLElement, optionLabel: string) {
  await userEvent.click(combobox);
  // Предыдущий закрытый dropdown может ещё оставаться в DOM (анимация закрытия) — берём последний, самый свежий.
  const dropdown = await waitFor(() => {
    const nodes = document.querySelectorAll(".ant-select-dropdown-list");
    if (nodes.length === 0) throw new Error("Выпадающий список ещё не отрисован");
    return nodes[nodes.length - 1] as HTMLElement;
  });
  await userEvent.click(within(dropdown).getByText(optionLabel));
}

/** Фильтр `TransactionsPage`: combobox ищется по `aria-label`. */
async function chooseOption(comboboxName: string, optionLabel: string) {
  await chooseFromDropdown(screen.getByRole("combobox", { name: comboboxName }), optionLabel);
}

/** Поле `TransactionForm` (без `aria-label`) — combobox ищется по подписи `Form.Item` внутри открытого диалога. */
async function fillFormOption(labelText: string, optionLabel: string) {
  const label = screen.getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  await chooseFromDropdown(within(formItem).getByRole("combobox"), optionLabel);
}

/** Клик по видимой подписи `Segmented`, скоуп — сама группа фильтра типа (текст «Доход» дублируется в Tag карточки). */
async function chooseTypeFilter(label: "Все" | "Доход" | "Расход") {
  const group = screen.getByRole("radiogroup", { name: "Тип" });
  await userEvent.click(within(group).getByText(label));
}

async function goToPage(pageNumber: number) {
  await userEvent.click(screen.getByTitle(String(pageNumber)));
}

describe("TransactionsPage", () => {
  it("загрузка и рендер списка карточек", async () => {
    const { wrapper } = setup(defaultTransactionsHandler());
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Зарплата")).toBeInTheDocument();
    expect(screen.getByText("Наличные")).toBeInTheDocument();
  });

  it("пустой список показывает EmptyState, кнопка действия открывает форму создания", async () => {
    const { wrapper } = setup(() => page([]));
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Операций пока нет")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Создать операцию" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("фильтр по кошельку передаёт wallet_id и сбрасывает страницу на 1", async () => {
    const { api, wrapper } = setup(defaultTransactionsHandler({ total: 40 }));
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    // переключаемся на вторую страницу, затем меняем фильтр — страница должна сброситься на первую
    await goToPage(2);
    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({
        query: { offset: DEFAULT_PAGE_SIZE },
      }),
    );

    await chooseOption("Кошелёк", "Наличные");

    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({
        query: { wallet_id: "w1", offset: 0 },
      }),
    );
  });

  it("фильтр по категории передаёт category_id", async () => {
    const { api, wrapper } = setup(defaultTransactionsHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await chooseOption("Категория", "Продукты");

    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({ query: { category_id: "c2" } }),
    );
  });

  it("фильтр по диапазону дат передаёт date_from/date_to", async () => {
    const { api, wrapper } = setup(defaultTransactionsHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await userEvent.type(screen.getByPlaceholderText("Дата от"), "2026-03-01");
    await userEvent.keyboard("{Enter}");
    await userEvent.type(screen.getByPlaceholderText("Дата до"), "2026-03-10");
    await userEvent.keyboard("{Enter}");

    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({
        // Формат ISO зависит от локальной таймзоны окружения теста, поэтому сравнение — тем же способом.
        query: {
          date_from: dayjs("2026-03-01").startOf("day").toISOString(),
          date_to: dayjs("2026-03-10").endOf("day").toISOString(),
        },
      }),
    );
  });

  it("фильтр по типу передаёт type", async () => {
    const { api, wrapper } = setup(defaultTransactionsHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await chooseTypeFilter("Доход");

    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({ query: { type: "income" } }),
    );
  });

  it("комбинация нескольких фильтров одновременно", async () => {
    const { api, wrapper } = setup(defaultTransactionsHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await chooseOption("Кошелёк", "Наличные");
    await chooseOption("Категория", "Зарплата");
    await chooseTypeFilter("Доход");

    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({
        query: { wallet_id: "w1", category_id: "c1", type: "income" },
      }),
    );
  });

  it("переключение страницы запрашивает нужный offset", async () => {
    const { api, wrapper } = setup(defaultTransactionsHandler({ total: 40 }));
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await goToPage(2);

    await waitFor(() =>
      expect(transactionsRequests(api).at(-1)).toMatchObject({
        query: { offset: DEFAULT_PAGE_SIZE, limit: DEFAULT_PAGE_SIZE },
      }),
    );
  });

  it("карточка баланса показывается только при конкретном фильтре «Кошелёк»", async () => {
    const { api, wrapper } = setup((request) => {
      if (request.path.startsWith("/api/wallets/") && request.path.endsWith("/balances")) {
        return [{ currency_id: "cur1", balance: "100.00" }];
      }
      return page(TRANSACTIONS);
    });
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    expect(api.requests.some((r) => r.path.endsWith("/balances"))).toBe(false);

    await chooseOption("Кошелёк", "Наличные");

    expect(await screen.findByText("USD: 100.00")).toBeInTheDocument();
  });

  it("кнопка «Редактировать» карточки открывает форму с ожидаемыми пропами", async () => {
    const { wrapper } = setup(defaultTransactionsHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));

    expect(await screen.findByText("Редактировать операцию")).toBeInTheDocument();
  });

  it("ошибка загрузки показывает toast (общий обработчик)", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });
    render(<TransactionsPage />, { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });

  it("сквозной сценарий: создание убирает EmptyState, редактирование обновляет карточку, удаление возвращает к EmptyState", async () => {
    let items: unknown[] = [];
    const handler: FakeHandler = (request) => {
      if (request.path === "/api/transactions" && request.method === "GET") return page(items);
      if (request.path === "/api/transactions" && request.method === "POST") {
        const body = request.body as {
          wallet_id: string;
          category_id: string;
          currency_id: string;
          amount: string;
        };
        const created = {
          id: "new1",
          wallet_id: body.wallet_id,
          category_id: body.category_id,
          legs: [{ currency_id: body.currency_id, amount: body.amount }],
          occurred_at: "2026-03-15T00:00:00Z",
          created_at: "2026-03-15T00:00:00Z",
          updated_at: null,
        };
        items = [created];
        return created;
      }
      if (request.path === "/api/transactions/new1" && request.method === "PUT") {
        const body = request.body as { currency_id: string; amount: string };
        const updated = {
          ...(items[0] as Record<string, unknown>),
          legs: [{ currency_id: body.currency_id, amount: body.amount }],
        };
        items = [updated];
        return updated;
      }
      if (request.path === "/api/transactions/new1" && request.method === "DELETE") {
        items = [];
        return undefined;
      }
      return page(items);
    };
    const { wrapper } = setup(handler);
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Операций пока нет")).toBeInTheDocument();

    // создание
    await userEvent.click(screen.getByRole("button", { name: "Создать операцию" }));
    await fillFormOption("Кошелёк", "Наличные");
    await fillFormOption("Категория", "Зарплата");
    await fillFormOption("Валюта", "USD — Доллар США");
    let dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Сумма"), "10");
    await userEvent.click(within(dialog).getByRole("button", { name: "Создать" }));

    // Карточка отображает сумму+код валюты уникальным текстом (в отличие от «Зарплата» — оно же остаётся
    // выбранным значением в закрывающемся, но не сразу размонтированном Drawer).
    expect(await screen.findByText("10 USD")).toBeInTheDocument();
    expect(screen.queryByText("Операций пока нет")).not.toBeInTheDocument();

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

    expect(await screen.findByText("Операций пока нет")).toBeInTheDocument();
  });

  it("успешная мутация операции перезапрашивает баланс открытой карточки выбранного кошелька", async () => {
    let items: unknown[] = [];
    const handler: FakeHandler = (request) => {
      if (request.path === "/api/transactions" && request.method === "GET") return page(items);
      if (request.path === "/api/transactions" && request.method === "POST") {
        const body = request.body as {
          wallet_id: string;
          category_id: string;
          currency_id: string;
          amount: string;
        };
        const created = {
          id: "new1",
          wallet_id: body.wallet_id,
          category_id: body.category_id,
          legs: [{ currency_id: body.currency_id, amount: body.amount }],
          occurred_at: "2026-03-15T00:00:00Z",
          created_at: "2026-03-15T00:00:00Z",
          updated_at: null,
        };
        items = [created];
        return created;
      }
      if (request.path.endsWith("/balances")) return [{ currency_id: "cur1", balance: "0.00" }];
      return page(items);
    };
    const { api, wrapper } = setup(handler);
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Операций пока нет");

    await chooseOption("Кошелёк", "Наличные");
    await screen.findByText("USD: 0.00");
    await waitFor(() =>
      expect(api.requests.filter((r) => r.path.endsWith("/balances"))).toHaveLength(1),
    );

    await userEvent.click(screen.getByRole("button", { name: "Создать операцию" }));
    await fillFormOption("Кошелёк", "Наличные");
    await fillFormOption("Категория", "Зарплата");
    await fillFormOption("Валюта", "USD — Доллар США");
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Сумма"), "10");
    await userEvent.click(within(dialog).getByRole("button", { name: "Создать" }));

    await waitFor(() =>
      expect(api.requests.filter((r) => r.path.endsWith("/balances")).length).toBeGreaterThan(1),
    );
  });
});
