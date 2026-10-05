import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import { describe, expect, it, vi } from "vitest";
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

describe("TransactionCard", () => {
  it("отображает все резолвленные поля карточки (одна нога — регресс)", () => {
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("Зарплата")).toBeInTheDocument();
    expect(screen.queryByText("Доход")).not.toBeInTheDocument();
    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    // Формат даты зависит от локальной таймзоны окружения теста, поэтому она сравнивается тем же способом.
    expect(
      screen.getByText(`Наличные · ${dayjs(TRANSACTION.occurred_at).format("DD.MM.YYYY HH:mm")}`),
    ).toBeInTheDocument();
  });

  it("отображает комментарий, если он задан", () => {
    render(
      <TransactionCard
        transaction={{ ...TRANSACTION, comment: "Серый рюкзак" }}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("Серый рюкзак")).toBeInTheDocument();
  });

  it("не рендерит строку комментария, если он не задан", () => {
    const { container } = render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
    );

    // Комментарий — единственный необязательный текстовый блок карточки; проверяем количество
    // `Typography.Text[type=secondary]`, а не конкретный текст, которого по определению нет.
    expect(container.querySelectorAll(".ant-typography-secondary")).toHaveLength(1);
  });

  it("отображает список строк с суммами всех валют при нескольких ногах", () => {
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    expect(screen.getByText("300.00 RUB")).toBeInTheDocument();
  });

  it("рендерится без падения, пока walletName/category не резолвлены, а код валюты отсутствует в карте", () => {
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName={undefined}
        category={undefined}
        currencyCodeById={new Map()}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("нажатие на карточку вызывает onEdit с операцией (в том числе при нескольких ногах)", async () => {
    const onEdit = vi.fn();
    render(
      <TransactionCard
        transaction={MULTI_LEG_TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={onEdit}
      />,
    );

    await userEvent.click(screen.getByText("Зарплата"));

    expect(onEdit).toHaveBeenCalledWith(MULTI_LEG_TRANSACTION);
  });

  it("Enter и пробел на карточке вызывают onEdit", async () => {
    const onEdit = vi.fn();
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={onEdit}
      />,
    );

    screen.getByRole("button").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");

    expect(onEdit).toHaveBeenCalledTimes(2);
  });

  it("не содержит кнопок «Редактировать» и «Удалить»", () => {
    render(
      <TransactionCard
        transaction={TRANSACTION}
        walletName="Наличные"
        category={{ name: "Зарплата", icon: "banknote" }}
        currencyCodeById={CURRENCY_CODE_BY_ID}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Редактировать" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Удалить" })).not.toBeInTheDocument();
  });
});
