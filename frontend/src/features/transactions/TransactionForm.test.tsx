import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { setMedia } from "@/test/matchMedia";
import type { Transaction } from "./Transaction";
import { TransactionForm } from "./TransactionForm";

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

const TRANSACTION: Transaction = {
  id: "t1",
  wallet_id: "w2",
  category_id: "c2",
  legs: [{ currency_id: "cur2", amount: "25.00" }],
  occurred_at: "2026-02-01T10:00:00Z",
  comment: null,
  created_at: "2026-02-01T10:00:00Z",
  updated_at: null,
};

function page(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`) return page(WALLETS);
    if (request.path === "/api/currencies") return page(CURRENCIES);
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories`) {
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
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>
          <ToastProvider>{children}</ToastProvider>
        </WorkspaceContext.Provider>
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

/** Текст выбранного значения `Select` по подписи поля, `null` — если ничего не выбрано. */
function selectedLabel(labelText: string): string | null {
  const content = formControl(labelText).closest(".ant-select-content");
  return content?.getAttribute("title") ?? null;
}

async function fillMinimalForm() {
  await selectOption("Кошелёк", "Наличные");
  await selectOption("Категория", "Продукты");
  await userEvent.type(screen.getByLabelText("Сумма (USD)"), "10");
}

describe("TransactionForm", () => {
  it("создание: тело запроса без валюты и типа", async () => {
    const CREATED = {
      id: "9",
      wallet_id: "w1",
      category_id: "c2",
      legs: [{ currency_id: "cur1", amount: "10" }],
      occurred_at: "2026-01-01T00:00:00Z",
      comment: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) => r.method === "POST" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transactions`,
    );
    expect(request).toMatchObject({
      body: { wallet_id: "w1", category_id: "c2", amount: "10" },
    });
    expect(request?.body).not.toHaveProperty("currency_id");
    expect(request?.body).not.toHaveProperty("type");
    expect(await screen.findByText("Расход создан")).toBeInTheDocument();
  });

  it("«Добавить ещё»: после создания форма остаётся открытой, сумма очищена, кошелёк и категория сохранены", async () => {
    const { wrapper } = setup(() => ({}));
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("checkbox", { name: "Добавить ещё" }));
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Расход создан")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Сумма (USD)")).toHaveValue(""));
    expect(onClose).not.toHaveBeenCalled();
    expect(selectedLabel("Кошелёк")).toBe("Наличные");
    expect(selectedLabel("Категория")).toBe("Продукты");
    expect(screen.getByRole("checkbox", { name: "Добавить ещё" })).toBeChecked();
  });

  it("«Добавить ещё»: флажок в форме редактирования отсутствует", () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open transaction={TRANSACTION} onClose={vi.fn()} />, { wrapper });

    expect(screen.queryByRole("checkbox", { name: "Добавить ещё" })).not.toBeInTheDocument();
  });

  it("создание с комментарием: тело запроса содержит comment", async () => {
    const { api, wrapper } = setup(() => ({}));
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.type(screen.getByLabelText("Комментарий"), "Серый рюкзак");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find((r) => r.method === "POST");
    expect(request?.body).toMatchObject({ comment: "Серый рюкзак" });
  });

  it("валюта не выбирается: подпись суммы показывает код валюты кошелька", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    expect(screen.queryByText("Валюта")).not.toBeInTheDocument();
    expect(screen.getByText("Сумма")).toBeInTheDocument();

    await selectOption("Кошелёк", "Карта");
    expect(await screen.findByLabelText("Сумма (RUB)")).toBeInTheDocument();

    await selectOption("Кошелёк", "Наличные");
    expect(await screen.findByLabelText("Сумма (USD)")).toBeInTheDocument();
  });

  it("категория предлагает только расходные", async () => {
    const { api, wrapper } = setup(() => ({}));
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    await userEvent.click(formControl("Категория"));

    expect(await screen.findByText("Продукты")).toBeInTheDocument();
    expect(screen.queryByText("Зарплата")).not.toBeInTheDocument();
    expect(screen.queryByText("Тип")).not.toBeInTheDocument();
    expect(
      api.requests.some(
        (r) =>
          r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories` &&
          r.query?.type === "expense",
      ),
    ).toBe(true);
  });

  it("редактирование: поля предзаполнены по данным расхода", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransactionForm open transaction={TRANSACTION} onClose={vi.fn()} />, { wrapper });

    await waitFor(() => expect(selectedLabel("Кошелёк")).toBe("Карта"));
    expect(await screen.findByText("Продукты")).toBeInTheDocument();
    expect(screen.getByLabelText("Сумма (RUB)")).toHaveValue("25.00");
  });

  it("редактирование: комментарий предзаполнен, пустой комментарий при сохранении очищает его", async () => {
    const WITH_COMMENT = { ...TRANSACTION, comment: "Исходный комментарий" };
    const CLEARED = { ...WITH_COMMENT, comment: null };
    const { api, wrapper } = setup(() => CLEARED);
    const onClose = vi.fn();
    render(<TransactionForm open transaction={WITH_COMMENT} onClose={onClose} />, { wrapper });

    await waitFor(() =>
      expect(screen.getByLabelText("Комментарий")).toHaveValue("Исходный комментарий"),
    );

    await userEvent.clear(screen.getByLabelText("Комментарий"));
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) =>
        r.method === "PUT" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/t1`,
    );
    expect(request?.body).toMatchObject({ comment: "" });
  });

  it("успешное редактирование вызывает PUT и закрывает форму", async () => {
    const UPDATED = { ...TRANSACTION, legs: [{ currency_id: "cur2", amount: "30.00" }] };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<TransactionForm open transaction={TRANSACTION} onClose={onClose} />, { wrapper });

    await waitFor(() => expect(screen.getByLabelText("Сумма (RUB)")).toHaveValue("25.00"));
    await userEvent.clear(screen.getByLabelText("Сумма (RUB)"));
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "30.00");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/t1`,
      body: { wallet_id: "w2", category_id: "c2", amount: "30.00" },
    });
    expect(await screen.findByText("Расход обновлён")).toBeInTheDocument();
  });

  it("редактирование: «Удалить» с подтверждением вызывает DELETE и закрывает форму", async () => {
    const { api, wrapper } = setup(() => undefined);
    const onClose = vi.fn();
    render(<TransactionForm open transaction={TRANSACTION} onClose={onClose} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(await screen.findByText("Удалить расход?")).toBeInTheDocument();
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests).toContainEqual(
      expect.objectContaining({
        method: "DELETE",
        path: `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/t1`,
      }),
    );
  });

  it("редактирование: отмена подтверждения не удаляет и не закрывает форму", async () => {
    const { api, wrapper } = setup(() => undefined);
    const onClose = vi.fn();
    render(<TransactionForm open transaction={TRANSACTION} onClose={onClose} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Отмена" }));

    expect(api.requests.some((r) => r.method === "DELETE")).toBe(false);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("создание: кнопки «Удалить» нет", () => {
    const { wrapper } = setup(() => undefined);
    render(<TransactionForm open onClose={vi.fn()} />, { wrapper });

    expect(screen.queryByRole("button", { name: "Удалить" })).not.toBeInTheDocument();
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

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Сумма должна быть положительной")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("текстовая ошибка бизнес-правила backend показывается toast без падения формы", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        detail: "Сумма превышает допустимое число знаков для валюты RUB",
      });
    });
    const onClose = vi.fn();
    render(<TransactionForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(
      await screen.findByText(
        "Проверьте заполнение формы: Сумма превышает допустимое число знаков для валюты RUB",
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
