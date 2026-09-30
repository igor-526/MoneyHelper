import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import type { Transaction } from "./Transaction";
import { TransactionCard } from "./TransactionCard";

const CURRENCY_CODE_BY_ID = new Map([
  ["cur1", "USD"],
  ["cur2", "RUB"],
]);

const TRANSACTION: Transaction = {
  id: "t1",
  wallet_id: "w1",
  category_id: "c1",
  legs: [{ currency_id: "cur1", amount: "150.00" }],
  occurred_at: "2026-03-05T12:30:00Z",
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
      <ApiClientProvider client={api}>{children}</ApiClientProvider>
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
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getByText("Зарплата")).toBeInTheDocument();
    expect(screen.getByText("Доход")).toBeInTheDocument();
    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    // Формат зависит от локальной таймзоны окружения теста, поэтому дата сравнивается тем же способом.
    expect(
      screen.getByText(dayjs(TRANSACTION.occurred_at).format("DD.MM.YYYY HH:mm")),
    ).toBeInTheDocument();
  });

  it("отображает список строк с суммами всех валют при нескольких ногах", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
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
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={onEdit}
      />,
      { wrapper },
    );

    const editButton = screen.getByRole("button", { name: "Редактировать" });
    expect(editButton).toBeEnabled();
    await userEvent.click(editButton);

    expect(onEdit).toHaveBeenCalledWith(TRANSACTION);
  });

  it("кнопка «Редактировать» недоступна и показывает подсказку при нескольких ногах", async () => {
    const { wrapper } = setup(() => undefined);
    const onEdit = vi.fn();
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={onEdit}
      />,
      { wrapper },
    );

    const editButton = screen.getByRole("button", { name: "Редактировать" });
    expect(editButton).toBeDisabled();
    await userEvent.click(editButton);
    expect(onEdit).not.toHaveBeenCalled();

    await userEvent.hover(editButton);
    expect(
      await screen.findByText(
        "Пополнение с несколькими валютами нельзя редактировать — удалите и создайте заново",
      ),
    ).toBeInTheDocument();
  });

  it("кнопка «Удалить» кликабельна при одной ноге: подтверждение вызывает DELETE /api/transactions/{id}", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some((r) => r.method === "DELETE" && r.path === "/api/transactions/t1"),
      ).toBe(true),
    );
  });

  it("кнопка «Удалить» кликабельна при нескольких ногах: подтверждение вызывает DELETE /api/transactions/{id}", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some((r) => r.method === "DELETE" && r.path === "/api/transactions/t2"),
      ).toBe(true),
    );
  });

  it("отмена подтверждения не вызывает запрос", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote", type: "income" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
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
