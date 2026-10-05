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
import { TopupForm } from "./TopupForm";

const TEST_WORKSPACE_ID = "workspace-1";

const WALLETS = [
  {
    id: "w1",
    name: "Основной",
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

const INCOME_CATEGORIES = [
  {
    id: "c1",
    type: "income",
    name: "Зарплата",
    icon: "banknote",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
];

function page(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

const WORKSPACE = {
  id: TEST_WORKSPACE_ID,
  name: "Основной",
  currency_id: "cur1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const TOPUP: Transaction = {
  id: "t1",
  wallet_id: "w2",
  category_id: "c1",
  legs: [
    { currency_id: "cur1", amount: "10000.00" },
    { currency_id: "cur2", amount: "780.00" },
  ],
  occurred_at: "2026-02-01T10:00:00Z",
  comment: "Обмен",
  created_at: "2026-02-01T10:00:00Z",
  updated_at: null,
};

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/workspaces") return page([WORKSPACE]);
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`) return page(WALLETS);
    if (request.path === "/api/currencies") return page(CURRENCIES);
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories`) {
      expect(request.query?.type).toBe("income");
      return page(INCOME_CATEGORIES);
    }
    return handler(request);
  };
}

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

function formControl(labelText: string): HTMLElement {
  const label = screen.getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  return within(formItem).getByRole("combobox");
}

async function selectOption(labelText: string, optionLabel: string) {
  await userEvent.click(formControl(labelText));
  await userEvent.click(await screen.findByText(optionLabel));
}

describe("TopupForm", () => {
  it("кошелёк в валюте воркспейса строит одно поле суммы", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Основной");

    expect(await screen.findByLabelText("Сумма (USD)")).toBeInTheDocument();
    expect(screen.queryByLabelText("Сумма (RUB)")).not.toBeInTheDocument();
  });

  it("кошелёк в другой валюте строит два поля: валюта воркспейса и валюта кошелька", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Карта");

    expect(await screen.findByLabelText("Сумма (USD)")).toBeInTheDocument();
    expect(screen.getByLabelText("Сумма (RUB)")).toBeInTheDocument();
  });

  it("смена кошелька сбрасывает суммы и перестраивает поля", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Основной");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");

    await selectOption("Кошелёк", "Карта");

    expect(await screen.findByLabelText("Сумма (RUB)")).toHaveValue("");
    expect(screen.getByLabelText("Сумма (USD)")).toHaveValue("");
  });

  it("категория предлагает только доходные (запрос с type=income)", async () => {
    const { api, wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Категория", "Зарплата");

    expect(
      api.requests.some(
        (r) =>
          r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories` &&
          r.query?.type === "income",
      ),
    ).toBe(true);
  });

  it("успешное создание в другой валюте отправляет две ноги на /topups", async () => {
    const { api, wrapper } = setup(() => TOPUP);
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Карта");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10000");
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "780");
    await selectOption("Категория", "Зарплата");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) => r.method === "POST" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/topups`,
    );
    expect(request?.body).toMatchObject({
      wallet_id: "w2",
      category_id: "c1",
      legs: [
        { currency_id: "cur1", amount: "10000" },
        { currency_id: "cur2", amount: "780" },
      ],
    });
  });

  it("«Добавить ещё»: после создания форма остаётся открытой, суммы очищены, кошелёк сохранён", async () => {
    const { wrapper } = setup(() => TOPUP);
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Карта");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10000");
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "780");
    await selectOption("Категория", "Зарплата");
    await userEvent.click(screen.getByRole("checkbox", { name: "Добавить ещё" }));
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Пополнение создано")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Сумма (USD)")).toHaveValue(""));
    expect(screen.getByLabelText("Сумма (RUB)")).toHaveValue("");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("«Добавить ещё»: флажок в форме редактирования отсутствует", () => {
    const { wrapper } = setup(() => TOPUP);
    render(<TopupForm open transaction={TOPUP} onClose={vi.fn()} />, { wrapper });

    expect(screen.queryByRole("checkbox", { name: "Добавить ещё" })).not.toBeInTheDocument();
  });

  it("редактирование предзаполняет форму ногами и отправляет PUT /topups/{id}", async () => {
    const { api, wrapper } = setup(() => TOPUP);
    const onClose = vi.fn();
    render(<TopupForm open transaction={TOPUP} onClose={onClose} />, { wrapper });

    await waitFor(() => expect(screen.getByLabelText("Сумма (RUB)")).toHaveValue("780.00"));
    expect(screen.getByLabelText("Сумма (USD)")).toHaveValue("10000.00");
    expect(screen.getByLabelText("Комментарий")).toHaveValue("Обмен");

    await userEvent.clear(screen.getByLabelText("Сумма (RUB)"));
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "800");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/topups/t1`,
      body: {
        wallet_id: "w2",
        category_id: "c1",
        legs: [
          { currency_id: "cur1", amount: "10000.00" },
          { currency_id: "cur2", amount: "800" },
        ],
        comment: "Обмен",
      },
    });
    expect(await screen.findByText("Пополнение обновлено")).toBeInTheDocument();
  });

  it("редактирование: «Удалить» с подтверждением вызывает DELETE и закрывает форму", async () => {
    const { api, wrapper } = setup(() => undefined);
    const onClose = vi.fn();
    render(<TopupForm open transaction={TOPUP} onClose={onClose} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(await screen.findByText("Удалить пополнение?")).toBeInTheDocument();
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests).toContainEqual(
      expect.objectContaining({
        method: "DELETE",
        path: `/api/workspaces/${TEST_WORKSPACE_ID}/topups/t1`,
      }),
    );
  });

  it("редактирование: отмена подтверждения не удаляет и не закрывает форму", async () => {
    const { api, wrapper } = setup(() => undefined);
    const onClose = vi.fn();
    render(<TopupForm open transaction={TOPUP} onClose={onClose} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Отмена" }));

    expect(api.requests.some((r) => r.method === "DELETE")).toBe(false);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("создание: кнопки «Удалить» нет", () => {
    const { wrapper } = setup(() => undefined);
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    expect(screen.queryByRole("button", { name: "Удалить" })).not.toBeInTheDocument();
  });

  it("редактирование убирает лишние нули из сумм backend (8 знаков)", async () => {
    const raw = {
      ...TOPUP,
      legs: [
        { currency_id: "cur1", amount: "10000.00000000" },
        { currency_id: "cur2", amount: "780.00000000" },
      ],
    };
    const { wrapper } = setup(() => raw);
    render(<TopupForm open transaction={raw} onClose={vi.fn()} />, { wrapper });

    await waitFor(() => expect(screen.getByLabelText("Сумма (RUB)")).toHaveValue("780.00"));
    expect(screen.getByLabelText("Сумма (USD)")).toHaveValue("10000.00");
  });

  it("успешное создание отправляет одну ногу в валюте кошелька", async () => {
    const CREATED = {
      id: "1",
      wallet_id: "w1",
      category_id: "c1",
      legs: [{ currency_id: "cur1", amount: "10" }],
      occurred_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Основной");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await selectOption("Категория", "Зарплата");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) => r.method === "POST" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/topups`,
    );
    expect(request?.body).toMatchObject({
      wallet_id: "w1",
      category_id: "c1",
      legs: [{ currency_id: "cur1", amount: "10" }],
    });
    expect(await screen.findByText("Пополнение создано")).toBeInTheDocument();
  });

  it("создание с комментарием: тело запроса содержит comment", async () => {
    const CREATED = {
      id: "1",
      wallet_id: "w1",
      category_id: "c1",
      legs: [{ currency_id: "cur1", amount: "10" }],
      occurred_at: "2026-01-01T00:00:00Z",
      comment: "Обмен в банке",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Основной");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await selectOption("Категория", "Зарплата");
    await userEvent.type(screen.getByLabelText("Комментарий"), "Обмен в банке");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) => r.method === "POST" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/topups`,
    );
    expect(request?.body).toMatchObject({ comment: "Обмен в банке" });
  });

  it("текстовая ошибка бизнес-правила показывается toast без падения формы", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        detail: "Набор валют пополнения не совпадает с набором валют кошелька",
      });
    });
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Основной");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await selectOption("Категория", "Зарплата");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(
      await screen.findByText(
        "Проверьте заполнение формы: Набор валют пополнения не совпадает с набором валют кошелька",
      ),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("ошибка по wallet_id/category_id остаётся в форме", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { category_id: ["Категория не является доходной"] },
      });
    });
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Основной");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await selectOption("Категория", "Зарплата");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Категория не является доходной")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});
