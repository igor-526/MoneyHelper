import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { AnalyticsPage } from "./AnalyticsPage";

const TEST_WORKSPACE_ID = "workspace-1";

const WALLETS = [
  {
    id: "w1",
    name: "Наличные",
    icon: "wallet",
    currency_id: "cur1",
    created_at: "",
    updated_at: null,
  },
  {
    id: "w2",
    name: "Карта",
    icon: "credit-card",
    currency_id: "cur1",
    created_at: "",
    updated_at: null,
  },
  {
    id: "w3",
    name: "Alipay",
    icon: "wallet",
    currency_id: "cur3",
    created_at: "",
    updated_at: null,
  },
];

const WORKSPACES = [
  { id: TEST_WORKSPACE_ID, name: "Дом", currency_id: "cur2", created_at: "", updated_at: null },
];

const CATEGORIES = [
  {
    id: "c1",
    type: "income",
    name: "Зарплата",
    icon: "banknote",
    created_at: "",
    updated_at: null,
  },
  { id: "c2", type: "expense", name: "Продукты", icon: "coins", created_at: "", updated_at: null },
  { id: "c3", type: "expense", name: "Кафе", icon: "coins", created_at: "", updated_at: null },
];

const CURRENCIES = [
  { id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 },
  { id: "cur2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
  { id: "cur3", code: "CNY", name: "Китайский юань", decimal_places: 2 },
  { id: "cur4", code: "USDT", name: "Tether", decimal_places: 2 },
];

function referencePage(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`)
      return referencePage(WALLETS);
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories`)
      return referencePage(
        CATEGORIES.filter(
          (category) => !request.query?.type || category.type === request.query.type,
        ),
      );
    if (request.path === "/api/workspaces") return referencePage(WORKSPACES);
    if (request.path === "/api/currencies") return referencePage(CURRENCIES);
    return handler(request);
  };
}

function analyticsResult(
  buckets: { group_key: string; income: string; expense: string }[],
  unconvertedCurrencies: string[] = [],
) {
  return {
    display_currency_id: "cur2",
    buckets,
    unconverted_currencies: unconvertedCurrencies,
  };
}

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(withFixtures(handler));
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

function analyticsRequests(api: FakeApiClient) {
  return api.requests.filter((r) => r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/analytics`);
}

const BUCKETS = [
  { group_key: "c2", income: "0", expense: "300.00" },
  { group_key: "c3", income: "0", expense: "700.00" },
];

function categoryNames() {
  return screen
    .getAllByRole("listitem")
    .map((item) => item.textContent ?? "")
    .map((text) => text.replace(/\d.*$/, "").trim());
}

describe("AnalyticsPage", () => {
  it("по умолчанию: режим «Категории», весь период, запрос расходов по категориям без дат", async () => {
    const { api, wrapper } = setup(() => analyticsResult(BUCKETS));
    render(<AnalyticsPage />, { wrapper });

    expect(await screen.findByText("По всем категориям")).toBeInTheDocument();
    expect(screen.getByText("Весь период")).toBeInTheDocument();
    expect(screen.getByText("Категории")).toBeInTheDocument();
    const query = analyticsRequests(api)[0]?.query;
    expect(query).toMatchObject({ group_by: "category", type: "expense" });
    expect(query?.date_from).toBeUndefined();
    expect(query?.date_to).toBeUndefined();
    expect(query?.display_currency).toBeUndefined();
  });

  it("список: итог «По всем категориям» первой строкой, затем категории по убыванию суммы в валюте воркспейса", async () => {
    const { wrapper } = setup(() => analyticsResult(BUCKETS));
    render(<AnalyticsPage />, { wrapper });

    await screen.findByText("По всем категориям");

    expect(categoryNames()).toEqual(["По всем категориям", "Кафе", "Продукты"]);
    expect(screen.getByText("1000.00 RUB")).toBeInTheDocument();
    expect(screen.getByText("700.00 RUB")).toBeInTheDocument();
    expect(screen.getByText("70.0%")).toBeInTheDocument();
  });

  it("кнопка сортировки меняет порядок на обратный", async () => {
    const { wrapper } = setup(() => analyticsResult(BUCKETS));
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText("По всем категориям");

    await userEvent.click(screen.getByRole("button", { name: "Сначала большие" }));

    expect(categoryNames()).toEqual(["По всем категориям", "Продукты", "Кафе"]);
    expect(screen.getByRole("button", { name: "Сначала меньшие" })).toBeInTheDocument();
  });

  it("представление «Диаграмма» показывает легенду с суммами и долями", async () => {
    const { wrapper } = setup(() => analyticsResult(BUCKETS));
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText("По всем категориям");

    await userEvent.click(screen.getByText("Диаграмма"));

    expect(screen.getByRole("img", { name: /Круговая диаграмма/ })).toBeInTheDocument();
    expect(screen.getByText("700.00 RUB · 70.0%")).toBeInTheDocument();
    expect(screen.queryByText("По всем категориям")).not.toBeInTheDocument();
  });

  it("кнопка «Месяц» запрашивает аналитику за текущий календарный месяц", async () => {
    const { api, wrapper } = setup(() => analyticsResult(BUCKETS));
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText("По всем категориям");

    await userEvent.click(screen.getByRole("button", { name: "Месяц" }));

    await waitFor(() => expect(analyticsRequests(api).at(-1)?.query).toHaveProperty("date_from"));
    const query = analyticsRequests(api).at(-1)?.query as Record<string, string>;
    expect(query.date_from).toBe(dayjs().startOf("month").toISOString());
    expect(query.date_to).toBe(dayjs().endOf("month").toISOString());
    expect(screen.getByText("Выбранный период")).toBeInTheDocument();
  });

  it("пустой результат показывает пустое состояние", async () => {
    const { wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });

    expect(await screen.findByText("Нет расходов за выбранный период")).toBeInTheDocument();
  });

  it("валюты без курса показываются предупреждением", async () => {
    const { wrapper } = setup(() => analyticsResult(BUCKETS, ["cur3"]));
    render(<AnalyticsPage />, { wrapper });

    expect(await screen.findByText(/Операции в валютах CNY не вошли в итоги/)).toBeInTheDocument();
  });

  it("ошибка загрузки показывает toast (общий обработчик)", async () => {
    const { toast, wrapper } = setup((request) => {
      if (request.path.endsWith("/analytics")) {
        throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
      }
      return undefined;
    });
    render(<AnalyticsPage />, { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });

  describe("режим «Трата»", () => {
    const DAY_BUCKETS = [
      { group_key: "2026-01-01", income: "0", expense: "100.00" },
      { group_key: "2026-01-03", income: "0", expense: "50.00" },
    ];

    async function openSpending(api: ReturnType<typeof setup>) {
      render(<AnalyticsPage />, { wrapper: api.wrapper });
      await userEvent.click(screen.getByText("Трата"));
      await screen.findByRole("img", { name: /График трат по дням/ });
    }

    async function chooseInFilters(comboboxName: string, optionLabel: string) {
      await userEvent.click(screen.getByRole("button", { name: "Фильтры" }));
      const dialog = await screen.findByRole("dialog");
      await userEvent.click(within(dialog).getByRole("combobox", { name: comboboxName }));
      const dropdown = await waitFor(() => {
        const nodes = document.querySelectorAll(".ant-select-dropdown-list");
        if (nodes.length === 0) throw new Error("Выпадающий список ещё не отрисован");
        return nodes[nodes.length - 1] as HTMLElement;
      });
      await userEvent.click(within(dropdown).getByText(optionLabel));
      await userEvent.click(within(dialog).getByRole("button", { name: "Применить" }));
    }

    it("запрашивает расходы по дням в поясе браузера и показывает итог и график", async () => {
      const api = setup(() => analyticsResult(DAY_BUCKETS));
      await openSpending(api);

      const query = analyticsRequests(api.api).at(-1)?.query;
      expect(query).toMatchObject({
        group_by: "day",
        type: "expense",
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      expect(query?.wallet_id).toBeUndefined();
      expect(query?.category_id).toBeUndefined();
      expect(screen.getByText("Всего: 150.00 RUB")).toBeInTheDocument();
    });

    it("без трат показывает пустое состояние", async () => {
      const api = setup(() => analyticsResult([]));
      render(<AnalyticsPage />, { wrapper: api.wrapper });
      await userEvent.click(screen.getByText("Трата"));

      expect(await screen.findByText("Нет расходов за выбранный период")).toBeInTheDocument();
    });

    it("«Применить» отправляет кошелёк и категорию, «Сбросить» их снимает", async () => {
      const api = setup(() => analyticsResult(DAY_BUCKETS));
      await openSpending(api);

      await chooseInFilters("Кошелёк", "Карта");
      await chooseInFilters("Категория", "Кафе");
      await waitFor(() =>
        expect(analyticsRequests(api.api).at(-1)?.query).toMatchObject({
          wallet_id: "w2",
          category_id: "c3",
        }),
      );

      await userEvent.click(screen.getByRole("button", { name: "Фильтры" }));
      const dialog = await screen.findByRole("dialog");
      await userEvent.click(within(dialog).getByRole("button", { name: "Сбросить" }));

      await waitFor(() => {
        const query = analyticsRequests(api.api).at(-1)?.query;
        expect(query?.wallet_id).toBeUndefined();
        expect(query?.category_id).toBeUndefined();
      });
    });

    it("в окне фильтров только расходные категории", async () => {
      const api = setup(() => analyticsResult(DAY_BUCKETS));
      await openSpending(api);

      await userEvent.click(screen.getByRole("button", { name: "Фильтры" }));
      const dialog = await screen.findByRole("dialog");
      await userEvent.click(within(dialog).getByRole("combobox", { name: "Категория" }));
      const dropdown = await waitFor(() => {
        const nodes = document.querySelectorAll(".ant-select-dropdown-list");
        if (nodes.length === 0) throw new Error("Выпадающий список ещё не отрисован");
        return nodes[nodes.length - 1] as HTMLElement;
      });

      expect(within(dropdown).getByText("Продукты")).toBeInTheDocument();
      expect(within(dropdown).queryByText("Зарплата")).not.toBeInTheDocument();
    });
  });
});
