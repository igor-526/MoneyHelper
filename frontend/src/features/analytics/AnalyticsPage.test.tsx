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
    currency_ids: ["cur1"],
    created_at: "",
    updated_at: null,
  },
  {
    id: "w2",
    name: "Карта",
    icon: "credit-card",
    currency_ids: ["cur1"],
    created_at: "",
    updated_at: null,
  },
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
];

const CURRENCIES = [
  { id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 },
  { id: "cur2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
];

function referencePage(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`)
      return referencePage(WALLETS);
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories`)
      return referencePage(CATEGORIES);
    if (request.path === "/api/currencies") return referencePage(CURRENCIES);
    return handler(request);
  };
}

function analyticsResult(
  buckets: { group_key: string; income: string; expense: string }[],
  unconvertedCurrencies: string[] = [],
) {
  return {
    display_currency_id: "cur1",
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

async function chooseDisplayCurrency(optionLabel: string) {
  const combobox = within(screen.getByRole("group", { name: "Валюта отображения" })).getByRole(
    "combobox",
  );
  await chooseFromDropdown(combobox, optionLabel);
}

async function chooseGroupBy(label: "Кошелёк" | "Категория" | "Валюта") {
  const group = screen.getByRole("radiogroup", { name: "Срез" });
  await userEvent.click(within(group).getByText(label));
}

async function chooseDateRange() {
  await userEvent.type(screen.getByPlaceholderText("Дата от"), "2026-03-01");
  await userEvent.keyboard("{Enter}");
  await userEvent.type(screen.getByPlaceholderText("Дата до"), "2026-03-10");
  await userEvent.keyboard("{Enter}");
}

/** Заполняет все три обязательных поля: валюту отображения, диапазон дат и срез. */
async function fillRequiredFields(groupBy: "Кошелёк" | "Категория" | "Валюта" = "Кошелёк") {
  await chooseDisplayCurrency("USD — Доллар США");
  await chooseDateRange();
  await chooseGroupBy(groupBy);
}

const INFO_MESSAGE = "Выберите валюту отображения, диапазон дат и срез, чтобы увидеть аналитику";

describe("AnalyticsPage", () => {
  it("пустое состояние: показывает Alert «недостаточно данных», запрос не выполняется", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });

    expect(await screen.findByText(INFO_MESSAGE)).toBeInTheDocument();
    expect(analyticsRequests(api)).toHaveLength(0);
  });

  it("заполнена только валюта отображения: запрос не выполняется", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText(INFO_MESSAGE);

    await chooseDisplayCurrency("USD — Доллар США");

    expect(screen.getByText(INFO_MESSAGE)).toBeInTheDocument();
    expect(analyticsRequests(api)).toHaveLength(0);
  });

  it("заполнены валюта отображения и диапазон дат, без среза: запрос не выполняется", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText(INFO_MESSAGE);

    await chooseDisplayCurrency("USD — Доллар США");
    await chooseDateRange();

    expect(screen.getByText(INFO_MESSAGE)).toBeInTheDocument();
    expect(analyticsRequests(api)).toHaveLength(0);
  });

  it("заполнен только срез: запрос не выполняется", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText(INFO_MESSAGE);

    await chooseGroupBy("Кошелёк");

    expect(screen.getByText(INFO_MESSAGE)).toBeInTheDocument();
    expect(analyticsRequests(api)).toHaveLength(0);
  });

  it("заполнены все три обязательных поля: запрос выполняется автоматически, без кнопки подтверждения", async () => {
    const { api, wrapper } = setup(() =>
      analyticsResult([{ group_key: "w1", income: "100.00", expense: "0" }]),
    );
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText(INFO_MESSAGE);

    expect(screen.queryByRole("button", { name: "Показать" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Применить" })).not.toBeInTheDocument();

    await fillRequiredFields("Кошелёк");

    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));
    expect(analyticsRequests(api)[0]).toMatchObject({
      query: {
        display_currency: "cur1",
        group_by: "wallet",
        date_from: dayjs("2026-03-01").startOf("day").toISOString(),
        date_to: dayjs("2026-03-10").endOf("day").toISOString(),
      },
    });
    expect(await screen.findByText("Наличные")).toBeInTheDocument();
  });

  it("индикатор загрузки во время ожидания ответа", async () => {
    let resolveResponse!: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolveResponse = resolve;
    });
    const { wrapper } = setup((request) =>
      request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/analytics`
        ? pending
        : analyticsResult([]),
    );
    render(<AnalyticsPage />, { wrapper });
    await screen.findByText(INFO_MESSAGE);

    await fillRequiredFields("Кошелёк");

    expect(document.querySelector(".ant-spin")).toBeInTheDocument();
    resolveResponse(analyticsResult([{ group_key: "w1", income: "1", expense: "0" }]));
    await waitFor(() => expect(document.querySelector(".ant-spin")).not.toBeInTheDocument());
  });

  it("сужающий фильтр «Кошелёк» передаёт wallet_id", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await fillRequiredFields("Кошелёк");
    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));

    await chooseOption("Кошелёк", "Наличные");

    await waitFor(() =>
      expect(analyticsRequests(api).at(-1)).toMatchObject({ query: { wallet_id: "w1" } }),
    );
  });

  it("сужающий фильтр «Категория» передаёт category_id", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await fillRequiredFields("Кошелёк");
    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));

    await chooseOption("Категория", "Продукты");

    await waitFor(() =>
      expect(analyticsRequests(api).at(-1)).toMatchObject({ query: { category_id: "c2" } }),
    );
  });

  it("сужающий фильтр «Тип» передаёт type", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await fillRequiredFields("Кошелёк");
    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));

    await chooseOption("Тип", "Доход");

    await waitFor(() =>
      expect(analyticsRequests(api).at(-1)).toMatchObject({ query: { type: "income" } }),
    );
  });

  it("сужающий фильтр «Валюта операции» передаёт currency_id", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await fillRequiredFields("Кошелёк");
    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));

    await chooseOption("Валюта операции", "RUB");

    await waitFor(() =>
      expect(analyticsRequests(api).at(-1)).toMatchObject({ query: { currency_id: "cur2" } }),
    );
  });

  it("комбинация нескольких сужающих фильтров передаётся одновременно", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await fillRequiredFields("Кошелёк");
    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));

    await chooseOption("Кошелёк", "Наличные");
    await chooseOption("Тип", "Расход");

    await waitFor(() =>
      expect(analyticsRequests(api).at(-1)).toMatchObject({
        query: { wallet_id: "w1", type: "expense" },
      }),
    );
  });

  it("значение «Все …» не передаёт соответствующий параметр", async () => {
    const { api, wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });
    await fillRequiredFields("Кошелёк");
    await waitFor(() => expect(analyticsRequests(api)).toHaveLength(1));

    expect(analyticsRequests(api)[0]?.query).toMatchObject({
      wallet_id: undefined,
      category_id: undefined,
      currency_id: undefined,
      type: undefined,
    });
  });

  it("срез «Кошелёк»: подпись карточки — название кошелька", async () => {
    const { wrapper } = setup(() =>
      analyticsResult([{ group_key: "w1", income: "100.00", expense: "0" }]),
    );
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");

    expect(await screen.findByText("Наличные")).toBeInTheDocument();
  });

  it("срез «Категория»: подпись карточки — название категории, без иконки и тега типа", async () => {
    const { wrapper } = setup(() =>
      analyticsResult([{ group_key: "c1", income: "100.00", expense: "0" }]),
    );
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Категория");

    expect(await screen.findByText("Зарплата")).toBeInTheDocument();
    expect(screen.queryByText("Доход", { selector: ".ant-tag" })).not.toBeInTheDocument();
  });

  it("срез «Валюта»: подпись карточки — код валюты", async () => {
    const { wrapper } = setup(() =>
      analyticsResult([{ group_key: "cur1", income: "100.00", expense: "0" }]),
    );
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Валюта");

    expect(await screen.findByText("USD")).toBeInTheDocument();
  });

  it("карточки отображаются в алфавитном порядке подписи, независимо от порядка ответа и величины сумм", async () => {
    const { wrapper } = setup(() =>
      analyticsResult([
        { group_key: "w1", income: "500.00", expense: "0" }, // «Наличные» — больше суммы, но позже по алфавиту
        { group_key: "w2", income: "5.00", expense: "0" }, // «Карта» — меньше суммы, но раньше по алфавиту
      ]),
    );
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");

    const labels = await waitFor(() => {
      const found = screen.getAllByText(/^(Карта|Наличные)$/);
      if (found.length !== 2) throw new Error("Карточки ещё не отрисованы");
      return found;
    });
    expect(labels.map((el) => el.textContent)).toEqual(["Карта", "Наличные"]);
  });

  it("пустой список корзин после успешного запроса: EmptyState «Нет данных за выбранный период»", async () => {
    const { wrapper } = setup(() => analyticsResult([]));
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");

    expect(await screen.findByText("Нет данных за выбранный период")).toBeInTheDocument();
  });

  it("предупреждение о валютах без курса отображается с корректными кодами", async () => {
    const { wrapper } = setup(() =>
      analyticsResult([{ group_key: "w1", income: "1", expense: "0" }], ["cur2"]),
    );
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");

    expect(
      await screen.findByText(
        "Не удалось пересчитать суммы в валютах: RUB — нет курса за выбранный период",
      ),
    ).toBeInTheDocument();
  });

  it("предупреждение отсутствует при пустом unconverted_currencies", async () => {
    const { wrapper } = setup(() =>
      analyticsResult([{ group_key: "w1", income: "1", expense: "0" }], []),
    );
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");
    await screen.findByText("Наличные");

    expect(screen.queryByText(/Не удалось пересчитать/)).not.toBeInTheDocument();
  });

  it("ошибка «неизвестная валюта отображения» показывает toast, список корзин не отображается", async () => {
    const { toast, wrapper } = setup((request) => {
      if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/analytics`) {
        throw new ApiError({
          kind: "validation",
          status: 400,
          detail: "Неизвестная валюта отображения",
        });
      }
      return analyticsResult([]);
    });
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Неизвестная валюта отображения"));
    expect(screen.queryByText("Наличные")).not.toBeInTheDocument();
  });

  it("ошибка «date_from позже date_to» показывает toast, список корзин не отображается", async () => {
    const { toast, wrapper } = setup((request) => {
      if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/analytics`) {
        throw new ApiError({ kind: "validation", status: 400, detail: "date_from позже date_to" });
      }
      return analyticsResult([]);
    });
    render(<AnalyticsPage />, { wrapper });

    await fillRequiredFields("Кошелёк");

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("date_from позже date_to"));
    expect(screen.queryByText("Наличные")).not.toBeInTheDocument();
  });
});
