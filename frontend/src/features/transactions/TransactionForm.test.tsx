import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import type { Transaction } from "./Transaction";
import { TransactionForm } from "./TransactionForm";

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

const TRANSACTION: Transaction = {
  id: "t1",
  wallet_id: "w1",
  category_id: "c2",
  legs: [{ currency_id: "cur2", amount: "25.00" }],
  occurred_at: "2026-02-01T10:00:00Z",
  created_at: "2026-02-01T10:00:00Z",
  updated_at: null,
};

function page(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/wallets") return page(WALLETS);
    if (request.path === "/api/currencies") return page(CURRENCIES);
    if (request.path === "/api/categories") {
      const type = request.query?.type as string | undefined;
      const items = type ? CATEGORIES.filter((c) => c.type === type) : CATEGORIES;
      return page(items);
    }
    return handler(request);
  };
}

/** Настоящий `ToastProvider`, чтобы проверять видимые уведомления, как использует их компонент. */
function setup(handler: FakeHandler) {
  const api = new FakeApiClient(withFixtures(handler));
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

/**
 * `CurrencyPicker` не пробрасывает `id` во внутренний `Select`, поэтому `getByLabelText` его не находит;
 * находим combobox через `Form.Item`, содержащий подпись поля — работает одинаково для обычных `Select` и
 * `CurrencyPicker`.
 */
function formControl(labelText: string): HTMLElement {
  const label = screen.getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  return within(formItem).getByRole("combobox");
}

async function selectOption(labelText: string, optionLabel: string) {
  await userEvent.click(formControl(labelText));
  await userEvent.click(await screen.findByText(optionLabel));
}

/** Текст выбранного значения `Select`/`CurrencyPicker` по подписи поля, `null` — если ничего не выбрано. */
function selectedLabel(labelText: string): string | null {
  const content = formControl(labelText).closest(".ant-select-content");
  return content?.getAttribute("title") ?? null;
}

/** Радио-инпут `Segmented` скрыт (`pointer-events: none`), клик идёт по видимой подписи. */
async function selectType(label: "Доход" | "Расход") {
  await userEvent.click(screen.getByText(label));
}

async function fillMinimalIncomeForm() {
  await selectOption("Кошелёк", "Наличные");
  await selectOption("Категория", "Зарплата");
  await selectOption("Валюта", "USD — Доллар США");
  await userEvent.type(screen.getByLabelText("Сумма"), "10");
}

describe("TransactionForm", () => {
  it("создание дохода: успех добавляет операцию, тело запроса не содержит поле типа", async () => {
    const CREATED = {
      id: "9",
      wallet_id: "w1",
      category_id: "c1",
      legs: [{ currency_id: "cur1", amount: "10" }],
      occurred_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalIncomeForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find((r) => r.method === "POST" && r.path === "/api/transactions");
    expect(request).toMatchObject({
      body: { wallet_id: "w1", category_id: "c1", currency_id: "cur1", amount: "10" },
    });
    expect(request?.body).not.toHaveProperty("type");
    expect(await screen.findByText("Операция создана")).toBeInTheDocument();
  });

  it("создание расхода: успех добавляет операцию, тело запроса не содержит поле типа", async () => {
    const CREATED = {
      id: "10",
      wallet_id: "w1",
      category_id: "c2",
      legs: [{ currency_id: "cur2", amount: "5" }],
      occurred_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await selectType("Расход");
    await selectOption("Кошелёк", "Наличные");
    await selectOption("Категория", "Продукты");
    await selectOption("Валюта", "RUB — Российский рубль");
    await userEvent.type(screen.getByLabelText("Сумма"), "5");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find((r) => r.method === "POST" && r.path === "/api/transactions");
    expect(request).toMatchObject({
      body: { wallet_id: "w1", category_id: "c2", currency_id: "cur2", amount: "5" },
    });
    expect(request?.body).not.toHaveProperty("type");
    expect(await screen.findByText("Операция создана")).toBeInTheDocument();
  });

  it("редактирование: поля и переключатель типа предзаполнены по данным операции", async () => {
    const { wrapper } = setup(() => TRANSACTION);
    render(<TransactionForm open transaction={TRANSACTION} onClose={vi.fn()} />, { wrapper });

    await screen.findByText("Продукты");
    expect(screen.getByRole("radio", { name: "Расход" })).toBeChecked();
    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getByText("RUB — Российский рубль")).toBeInTheDocument();
    expect(screen.getByLabelText("Сумма")).toHaveValue("25.00");
  });

  it("успешное редактирование вызывает PUT и закрывает форму", async () => {
    const UPDATED = { ...TRANSACTION, legs: [{ currency_id: "cur2", amount: "30.00" }] };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<TransactionForm open transaction={TRANSACTION} onClose={onClose} />, { wrapper });

    await screen.findByText("Продукты");
    await userEvent.clear(screen.getByLabelText("Сумма"));
    await userEvent.type(screen.getByLabelText("Сумма"), "30.00");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: "/api/transactions/t1",
      body: { wallet_id: "w1", category_id: "c2", currency_id: "cur2", amount: "30.00" },
    });
    expect(await screen.findByText("Операция обновлена")).toBeInTheDocument();
  });

  it("смена типа сбрасывает выбранную категорию", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Категория", "Зарплата");
    expect(selectedLabel("Категория")).toBe("Зарплата");

    await selectType("Расход");

    expect(selectedLabel("Категория")).toBeNull();
  });

  it("смена кошелька сбрасывает выбранную валюту", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Наличные");
    await selectOption("Валюта", "USD — Доллар США");
    expect(selectedLabel("Валюта")).toBe("USD — Доллар США");

    await selectOption("Кошелёк", "Карта");

    expect(selectedLabel("Валюта")).toBeNull();
  });

  it("список валют в CurrencyPicker ограничен набором выбранного кошелька", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Карта");
    await userEvent.click(formControl("Валюта"));

    expect(await screen.findByText("RUB — Российский рубль")).toBeInTheDocument();
    expect(screen.queryByText("USD — Доллар США")).not.toBeInTheDocument();
  });

  it("ошибка валидации по полю остаётся в форме и не закрывает её", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { amount: ["Сумма должна быть положительной"] },
      });
    });
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalIncomeForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Сумма должна быть положительной")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("текстовая ошибка бизнес-правила backend показывается toast без падения формы", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        detail: "Валюта операции не входит в набор валют кошелька",
      });
    });
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalIncomeForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(
      await screen.findByText(
        "Проверьте заполнение формы: Валюта операции не входит в набор валют кошелька",
      ),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});
