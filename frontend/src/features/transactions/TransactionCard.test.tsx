import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import type { Transaction } from "./Transaction";
import { TransactionCard } from "./TransactionCard";
import { useDeleteTopup } from "./useDeleteTopup";
import { useDeleteTransaction } from "./useDeleteTransaction";

const TEST_WORKSPACE_ID = "workspace-1";

const CURRENCY_CODE_BY_ID = new Map([
  ["cur1", "USD"],
  ["cur2", "RUB"],
]);

const KIND = { useDelete: useDeleteTransaction, deleteTitle: "Удалить расход?" };

const TOPUP_KIND = { useDelete: useDeleteTopup, deleteTitle: "Удалить пополнение?" };

const TRANSACTION: Transaction = {
  id: "t1",
  wallet_id: "w1",
  category_id: "c1",
  legs: [{ currency_id: "cur1", amount: "150.00" }],
  occurred_at: "2026-03-05T12:30:00Z",
  comment: null,
  created_at: "2026-03-05T12:30:00Z",
  updated_at: null,
};

const MULTI_LEG_TRANSACTION: Transaction = {
  ...TRANSACTION,
  id: "t2",
  legs: [
    { currency_id: "cur1", amount: "150.00" },
    { currency_id: "cur2", amount: "300.00" },
  ],
};

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>{children}</WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("TransactionCard", () => {
  it("отображает все резолвленные поля карточки (одна нога — регресс)", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getByText("Зарплата")).toBeInTheDocument();
    expect(screen.queryByText("Доход")).not.toBeInTheDocument();
    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    // Формат зависит от локальной таймзоны окружения теста, поэтому дата сравнивается тем же способом.
    expect(
      screen.getByText(dayjs(TRANSACTION.occurred_at).format("DD.MM.YYYY HH:mm")),
    ).toBeInTheDocument();
  });

  it("отображает комментарий, если он задан", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={{ ...TRANSACTION, comment: "Серый рюкзак" }}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("Серый рюкзак")).toBeInTheDocument();
  });

  it("не рендерит строку комментария, если он не задан", () => {
    const { wrapper } = setup(() => undefined);
    const { container } = render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    // Комментарий — единственный необязательный текстовый блок карточки; проверяем количество
    // `Typography.Text[type=secondary]`, а не конкретный текст, которого по определению нет.
    expect(container.querySelectorAll(".ant-typography-secondary")).toHaveLength(2);
  });

  it("отображает список строк с суммами всех валют при нескольких ногах", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    expect(screen.getByText("300.00 RUB")).toBeInTheDocument();
  });

  it("рендерится без падения, пока walletName/category не резолвлены, а код валюты отсутствует в карте", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName={undefined}
        category={undefined}
        currencyCodeById={new Map()}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByRole("button", { name: "Редактировать" })).toBeInTheDocument();
  });

  it("кнопка «Редактировать» кликабельна и вызывает onEdit при одной ноге", async () => {
    const { wrapper } = setup(() => undefined);
    const onEdit = vi.fn();
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={onEdit}
      />,
      { wrapper },
    );

    const editButton = screen.getByRole("button", { name: "Редактировать" });
    expect(editButton).toBeEnabled();
    await userEvent.click(editButton);

    expect(onEdit).toHaveBeenCalledWith(TRANSACTION);
  });

  it("кнопка «Редактировать» доступна и при нескольких ногах (пополнение)", async () => {
    const { wrapper } = setup(() => undefined);
    const onEdit = vi.fn();
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={onEdit}
      />,
      { wrapper },
    );

    const editButton = screen.getByRole("button", { name: "Редактировать" });
    expect(editButton).toBeEnabled();
    await userEvent.click(editButton);
    expect(onEdit).toHaveBeenCalledWith(MULTI_LEG_TRANSACTION);
  });

  it("кнопка «Удалить» кликабельна при одной ноге: подтверждение вызывает DELETE /api/transactions/{id}", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some(
          (r) =>
            r.method === "DELETE" &&
            r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/t1`,
        ),
      ).toBe(true),
    );
  });

  it("удаление пополнения вызывает DELETE /topups/{id} и показывает своё подтверждение", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={TOPUP_KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(await screen.findByText("Удалить пополнение?")).toBeInTheDocument();
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some(
          (r) =>
            r.method === "DELETE" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/topups/t2`,
        ),
      ).toBe(true),
    );
  });

  it("отмена подтверждения не вызывает запрос", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        kind={KIND}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Отмена" }));

    expect(api.requests).toHaveLength(0);
  });
});
