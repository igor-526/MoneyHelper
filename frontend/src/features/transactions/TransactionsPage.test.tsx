import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { DEFAULT_PAGE_SIZE } from "./useTransactions";
import { TransactionsPage } from "./TransactionsPage";

const TEST_WORKSPACE_ID = "workspace-1";

const WALLETS = [
  {
    id: "w1",
    name: "Наличные",
    icon: "wallet",
    currency_id: "cur1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "w2",
    name: "Карта",
    icon: "credit-card",
    currency_id: "cur2",
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

const TOPUP_LEGS_RUB = [{ currency_id: "cur1", amount: "10.00" }];

function operation(
  id: string,
  categoryId: string,
  legs: { currency_id: string; amount: string }[],
) {
  return {
    id,
    wallet_id: "w1",
    category_id: categoryId,
    legs,
    comment: null,
    occurred_at: "2026-03-01T12:00:00Z",
    created_at: "2026-03-01T12:00:00Z",
    updated_at: null,
  };
}

const TOPUPS = [operation("p1", "c1", TOPUP_LEGS_RUB)];
const EXPENSES = [operation("e1", "c2", [{ currency_id: "cur1", amount: "5.00" }])];

const WORKSPACE = {
  id: TEST_WORKSPACE_ID,
  name: "Основной",
  currency_id: "cur1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const TOPUPS_PATH = `/api/workspaces/${TEST_WORKSPACE_ID}/topups`;
const EXPENSES_PATH = `/api/workspaces/${TEST_WORKSPACE_ID}/transactions`;
const TRANSFERS_PATH = `/api/workspaces/${TEST_WORKSPACE_ID}/transfers`;

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

/** Обработчик по умолчанию: списки пополнений и расходов + нейтральные баланс и курс. */
function defaultHandler(
  overrides: Partial<{ topups: unknown[]; expenses: unknown[]; total: number }> = {},
): FakeHandler {
  return (request) => {
    if (request.path.endsWith("/balances")) return { currency_id: "cur1", balance: "100.00" };
    if (request.path === TOPUPS_PATH) return page(overrides.topups ?? TOPUPS, overrides);
    if (request.path === EXPENSES_PATH) return page(overrides.expenses ?? EXPENSES, overrides);
    return page([]);
  };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/workspaces") return page([WORKSPACE], { limit: 100 });
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`)
      return page(WALLETS, { limit: 100 });
    if (request.path === "/api/currencies") return page(CURRENCIES, { limit: 100 });
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories`) {
      const type = request.query?.type as string | undefined;
      const items = type ? CATEGORIES.filter((c) => c.type === type) : CATEGORIES;
      return page(items, { limit: 100 });
    }
    if (request.path.endsWith("/rates")) {
      return { workspace_currency_id: "cur1", wallet_currency_id: "cur1", rate: "1" };
    }
    return handler(request);
  };
}

function setup(handler: FakeHandler, path = "/transactions") {
  const api = new FakeApiClient(withFixtures(handler));
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>
          <ToastProvider>
            <MemoryRouter initialEntries={[path]}>
              <Routes>
                <Route path="/transactions" element={children} />
              </Routes>
            </MemoryRouter>
          </ToastProvider>
        </WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, toast, wrapper };
}

function requestsTo(api: FakeApiClient, path: string) {
  return api.requests.filter((r) => r.path === path && r.method === "GET");
}

/** Опция ищется внутри последнего выпадающего списка, а не по всему документу (тексты дублируют карточки). */
async function chooseFromDropdown(combobox: HTMLElement, optionLabel: string) {
  await userEvent.click(combobox);
  const dropdown = await waitFor(() => {
    const nodes = document.querySelectorAll(".ant-select-dropdown-list");
    if (nodes.length === 0) throw new Error("Выпадающий список ещё не отрисован");
    return nodes[nodes.length - 1] as HTMLElement;
  });
  await userEvent.click(within(dropdown).getByText(optionLabel));
}

/** Фильтр страницы: combobox ищется по `aria-label` внутри активной панели. */
async function chooseOption(comboboxName: string, optionLabel: string) {
  const panel = activePanel();
  await chooseFromDropdown(
    within(panel).getByRole("combobox", { name: comboboxName }),
    optionLabel,
  );
}

function activePanel(): HTMLElement {
  return document.querySelector<HTMLElement>('[role="tabpanel"][aria-hidden="false"]')!;
}

/** Поле формы (без `aria-label`) — combobox ищется по подписи `Form.Item`. */
async function fillFormOption(labelText: string, optionLabel: string) {
  const dialog = screen.getByRole("dialog");
  const label = within(dialog).getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  await chooseFromDropdown(within(formItem).getByRole("combobox"), optionLabel);
}

async function openTab(name: "Пополнение" | "Расход" | "Перевод") {
  await userEvent.click(screen.getByRole("tab", { name }));
}

async function goToPage(pageNumber: number) {
  await userEvent.click(within(activePanel()).getByTitle(String(pageNumber)));
}

async function confirmDelete() {
  await userEvent.click(within(activePanel()).getByRole("button", { name: "Удалить" }));
  const popup = await screen.findByRole("tooltip");
  await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));
}

describe("TransactionsPage", () => {
  it("по умолчанию открыта вкладка «Пополнение» со списком пополнений", async () => {
    const { api, wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Зарплата")).toBeInTheDocument();
    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Пополнение" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(requestsTo(api, EXPENSES_PATH)).toHaveLength(0);
  });

  it("неизвестное значение ?tab= открывает вкладку по умолчанию", async () => {
    const { wrapper } = setup(defaultHandler(), "/transactions?tab=unknown");
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Зарплата")).toBeInTheDocument();
  });

  it("переключение на «Расход» загружает расходы из /transactions", async () => {
    const { api, wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await openTab("Расход");

    expect(await screen.findByText("Продукты")).toBeInTheDocument();
    expect(requestsTo(api, EXPENSES_PATH)[0]?.query).not.toHaveProperty("type");
  });

  it("вкладка из ?tab=expense открывается сразу", async () => {
    const { wrapper } = setup(defaultHandler(), "/transactions?tab=expense");
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Продукты")).toBeInTheDocument();
  });

  it("фильтр категории показывает только категории типа вкладки", async () => {
    const { wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await userEvent.click(within(activePanel()).getByRole("combobox", { name: "Категория" }));
    const dropdown = await waitFor(() => {
      const nodes = document.querySelectorAll(".ant-select-dropdown-list");
      if (nodes.length === 0) throw new Error("не отрисован");
      return nodes[nodes.length - 1] as HTMLElement;
    });

    expect(within(dropdown).getByText("Все категории")).toBeInTheDocument();
    expect(within(dropdown).queryByText("Продукты")).not.toBeInTheDocument();
  });

  it("фильтры вкладки сохраняются при переключении вкладок", async () => {
    const { wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");
    await chooseOption("Кошелёк", "Карта");

    await openTab("Расход");
    await screen.findByText("Продукты");
    await openTab("Пополнение");

    const panel = activePanel();
    const wallet = within(panel).getByRole("combobox", { name: "Кошелёк" });
    expect(wallet.closest(".ant-select-content")).toHaveAttribute("title", "Карта");
  });

  it("ссылки «Переводы» нет, переводы — третья вкладка «Перевод»", async () => {
    const { wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    expect(screen.queryByText("Переводы")).not.toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
      "Пополнение",
      "Расход",
      "Перевод",
    ]);
  });

  it("вкладка «Перевод» загружает переводы и записывает tab=transfer", async () => {
    const { api, wrapper } = setup((request) =>
      request.path === TRANSFERS_PATH
        ? page([
            {
              id: "t1",
              from_wallet_id: "w1",
              to_wallet_id: "w2",
              amount: "7.00",
              occurred_at: "2026-03-01T12:00:00Z",
              created_at: "2026-03-01T12:00:00Z",
              updated_at: null,
            },
          ])
        : defaultHandler()(request),
    );
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await openTab("Перевод");

    expect(await screen.findByText("Наличные → Карта")).toBeInTheDocument();
    expect(requestsTo(api, TRANSFERS_PATH)).toHaveLength(1);
  });

  it("вкладка из ?tab=transfer открывается сразу", async () => {
    const { wrapper } = setup(defaultHandler(), "/transactions?tab=transfer");
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Переводов пока нет")).toBeInTheDocument();
  });

  it("пустая вкладка «Пополнение» показывает EmptyState, действие открывает форму пополнения", async () => {
    const { wrapper } = setup(defaultHandler({ topups: [] }));
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Пополнений пока нет")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Создать пополнение" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Создать пополнение")).toBeInTheDocument();
  });

  it("пустая вкладка «Расход» показывает EmptyState, действие открывает форму расхода", async () => {
    const { wrapper } = setup(defaultHandler({ expenses: [] }), "/transactions?tab=expense");
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Расходов пока нет")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Создать расход" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Создать расход")).toBeInTheDocument();
  });

  it("кнопка «Добавить» открывает форму своей вкладки", async () => {
    const { wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await userEvent.click(screen.getByRole("button", { name: "Добавить" }));

    expect(await screen.findByText("Создать пополнение")).toBeInTheDocument();
  });

  it("карточка пополнения с двумя ногами показывает обе суммы", async () => {
    const two = operation("p2", "c1", [
      { currency_id: "cur1", amount: "10.00" },
      { currency_id: "cur2", amount: "20.00" },
    ]);
    const { wrapper } = setup(defaultHandler({ topups: [two] }));
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("10.00 USD")).toBeInTheDocument();
    expect(screen.getByText("20.00 RUB")).toBeInTheDocument();
  });

  it("фильтр по кошельку передаёт wallet_id и сбрасывает страницу на 1", async () => {
    const { api, wrapper } = setup(defaultHandler({ total: 40 }));
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await goToPage(2);
    await waitFor(() =>
      expect(requestsTo(api, TOPUPS_PATH).at(-1)).toMatchObject({
        query: { offset: DEFAULT_PAGE_SIZE },
      }),
    );

    await chooseOption("Кошелёк", "Наличные");

    await waitFor(() =>
      expect(requestsTo(api, TOPUPS_PATH).at(-1)).toMatchObject({
        query: { wallet_id: "w1", offset: 0 },
      }),
    );
  });

  it("фильтры категории и дат передаются в запрос расходов", async () => {
    const { api, wrapper } = setup(defaultHandler(), "/transactions?tab=expense");
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Продукты");

    await chooseOption("Категория", "Продукты");
    const panel = activePanel();
    await userEvent.type(within(panel).getByPlaceholderText("Дата от"), "2026-03-01");
    await userEvent.keyboard("{Enter}");
    await userEvent.type(within(panel).getByPlaceholderText("Дата до"), "2026-03-10");
    await userEvent.keyboard("{Enter}");

    await waitFor(() =>
      expect(requestsTo(api, EXPENSES_PATH).at(-1)).toMatchObject({
        query: {
          category_id: "c2",
          date_from: dayjs("2026-03-01").startOf("day").toISOString(),
          date_to: dayjs("2026-03-10").endOf("day").toISOString(),
        },
      }),
    );
  });

  it("карточка баланса показывается только при конкретном фильтре «Кошелёк»", async () => {
    const { api, wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    expect(api.requests.some((r) => r.path.endsWith("/balances"))).toBe(false);

    await chooseOption("Кошелёк", "Наличные");

    expect(await screen.findByText("USD: 100.00")).toBeInTheDocument();
  });

  it("«Редактировать» открывает форму пополнения или расхода по вкладке", async () => {
    const { wrapper } = setup(defaultHandler());
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Зарплата");

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    expect(await screen.findByText("Редактировать пополнение")).toBeInTheDocument();
  });

  it("«Редактировать» на вкладке расходов открывает форму расхода", async () => {
    const { wrapper } = setup(defaultHandler(), "/transactions?tab=expense");
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Продукты");

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    expect(await screen.findByText("Редактировать расход")).toBeInTheDocument();
  });

  it("ошибка загрузки показывает toast (общий обработчик)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });
    render(<TransactionsPage />, { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });

  it("сквозной сценарий пополнения: создание в другой валюте (две ноги), редактирование, удаление", async () => {
    let items: unknown[] = [];
    const handler: FakeHandler = (request) => {
      if (request.path === TOPUPS_PATH && request.method === "POST") {
        const body = request.body as {
          wallet_id: string;
          category_id: string;
          legs: unknown[];
        };
        const created = {
          ...operation("new1", body.category_id, body.legs as never),
          wallet_id: body.wallet_id,
        };
        items = [created];
        return created;
      }
      if (request.path === `${TOPUPS_PATH}/new1` && request.method === "PUT") {
        const body = request.body as { legs: unknown[] };
        items = [{ ...(items[0] as object), legs: body.legs }];
        return items[0];
      }
      if (request.path === `${TOPUPS_PATH}/new1` && request.method === "DELETE") {
        items = [];
        return undefined;
      }
      return page(items);
    };
    const { wrapper } = setup(handler);
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Пополнений пока нет")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Создать пополнение" }));
    await fillFormOption("Кошелёк", "Карта");
    let dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Сумма (USD)"), "10000");
    await userEvent.type(within(dialog).getByLabelText("Сумма (RUB)"), "780");
    await fillFormOption("Категория", "Зарплата");
    await userEvent.click(within(dialog).getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("10000 USD")).toBeInTheDocument();
    expect(screen.getByText("780 RUB")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dialog).getByLabelText("Сумма (RUB)")).toHaveValue("780"));
    await userEvent.clear(within(dialog).getByLabelText("Сумма (RUB)"));
    await userEvent.type(within(dialog).getByLabelText("Сумма (RUB)"), "800");
    await userEvent.click(within(dialog).getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("800 RUB")).toBeInTheDocument();

    await confirmDelete();
    expect(await screen.findByText("Пополнений пока нет")).toBeInTheDocument();
  });

  it("сквозной сценарий расхода: создание, редактирование, удаление", async () => {
    let items: unknown[] = [];
    const handler: FakeHandler = (request) => {
      if (request.path === EXPENSES_PATH && request.method === "POST") {
        const body = request.body as { wallet_id: string; category_id: string; amount: string };
        const created = {
          ...operation("new1", body.category_id, [{ currency_id: "cur1", amount: body.amount }]),
          wallet_id: body.wallet_id,
        };
        items = [created];
        return created;
      }
      if (request.path === `${EXPENSES_PATH}/new1` && request.method === "PUT") {
        const body = request.body as { amount: string };
        items = [{ ...(items[0] as object), legs: [{ currency_id: "cur1", amount: body.amount }] }];
        return items[0];
      }
      if (request.path === `${EXPENSES_PATH}/new1` && request.method === "DELETE") {
        items = [];
        return undefined;
      }
      return page(items);
    };
    const { wrapper } = setup(handler, "/transactions?tab=expense");
    render(<TransactionsPage />, { wrapper });

    expect(await screen.findByText("Расходов пока нет")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Создать расход" }));
    await fillFormOption("Кошелёк", "Наличные");
    await fillFormOption("Категория", "Продукты");
    let dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Сумма (USD)"), "10");
    await userEvent.click(within(dialog).getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("10 USD")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dialog).getByLabelText("Сумма (USD)")).toHaveValue("10"));
    await userEvent.clear(within(dialog).getByLabelText("Сумма (USD)"));
    await userEvent.type(within(dialog).getByLabelText("Сумма (USD)"), "20");
    await userEvent.click(within(dialog).getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("20 USD")).toBeInTheDocument();

    await confirmDelete();
    expect(await screen.findByText("Расходов пока нет")).toBeInTheDocument();
  });

  it("создание операции перезапрашивает баланс и курс выбранного кошелька", async () => {
    let items: unknown[] = [];
    const handler: FakeHandler = (request) => {
      if (request.path === TOPUPS_PATH && request.method === "POST") {
        const body = request.body as { category_id: string; legs: unknown[] };
        items = [operation("new1", body.category_id, body.legs as never)];
        return items[0];
      }
      if (request.path.endsWith("/balances")) return { currency_id: "cur1", balance: "0.00" };
      return page(items);
    };
    const { api, wrapper } = setup(handler);
    render(<TransactionsPage />, { wrapper });
    await screen.findByText("Пополнений пока нет");

    await chooseOption("Кошелёк", "Наличные");
    await screen.findByText("USD: 0.00");
    const balanceCount = () => api.requests.filter((r) => r.path.endsWith("/balances")).length;
    const rateCount = () => api.requests.filter((r) => r.path.endsWith("/rates")).length;
    await waitFor(() => expect(balanceCount()).toBe(1));
    const ratesBefore = rateCount();

    await userEvent.click(screen.getByRole("button", { name: "Создать пополнение" }));
    await fillFormOption("Кошелёк", "Наличные");
    await fillFormOption("Категория", "Зарплата");
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Сумма (USD)"), "10");
    await userEvent.click(within(dialog).getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(balanceCount()).toBeGreaterThan(1));
    await waitFor(() => expect(rateCount()).toBeGreaterThan(ratesBefore));
  });
});
