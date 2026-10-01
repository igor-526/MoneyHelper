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
import { TopupForm } from "./TopupForm";

const TEST_WORKSPACE_ID = "workspace-1";

const WALLETS = [
  {
    id: "w1",
    name: "Мультивалютный",
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

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
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
  it("выбор кошелька строит поля сумм по числу его валют", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Мультивалютный");

    expect(await screen.findByLabelText("Сумма (USD)")).toBeInTheDocument();
    expect(screen.getByLabelText("Сумма (RUB)")).toBeInTheDocument();
  });

  it("смена кошелька сбрасывает суммы и перестраивает поля", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TopupForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Кошелёк", "Мультивалютный");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");

    await selectOption("Кошелёк", "Карта");

    expect(screen.queryByLabelText("Сумма (USD)")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Сумма (RUB)")).toHaveValue("");
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

  it("успешное создание отправляет legs в порядке currency_ids кошелька", async () => {
    const CREATED = {
      id: "1",
      wallet_id: "w1",
      category_id: "c1",
      legs: [
        { currency_id: "cur1", amount: "10" },
        { currency_id: "cur2", amount: "20" },
      ],
      occurred_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Мультивалютный");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "20");
    await selectOption("Категория", "Зарплата");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) =>
        r.method === "POST" &&
        r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/topups`,
    );
    expect(request?.body).toMatchObject({
      wallet_id: "w1",
      category_id: "c1",
      legs: [
        { currency_id: "cur1", amount: "10" },
        { currency_id: "cur2", amount: "20" },
      ],
    });
    expect(await screen.findByText("Пополнение создано")).toBeInTheDocument();
  });

  it("создание с комментарием: тело запроса содержит comment", async () => {
    const CREATED = {
      id: "1",
      wallet_id: "w1",
      category_id: "c1",
      legs: [
        { currency_id: "cur1", amount: "10" },
        { currency_id: "cur2", amount: "20" },
      ],
      occurred_at: "2026-01-01T00:00:00Z",
      comment: "Обмен в банке",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TopupForm open onClose={onClose} />, { wrapper });

    await selectOption("Кошелёк", "Мультивалютный");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "20");
    await selectOption("Категория", "Зарплата");
    await userEvent.type(screen.getByLabelText("Комментарий"), "Обмен в банке");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find(
      (r) =>
        r.method === "POST" &&
        r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/topups`,
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

    await selectOption("Кошелёк", "Мультивалютный");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "20");
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

    await selectOption("Кошелёк", "Мультивалютный");
    await userEvent.type(await screen.findByLabelText("Сумма (USD)"), "10");
    await userEvent.type(screen.getByLabelText("Сумма (RUB)"), "20");
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
