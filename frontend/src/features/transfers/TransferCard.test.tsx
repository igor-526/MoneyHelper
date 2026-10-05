import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import { describe, expect, it, vi } from "vitest";
import type { Transfer } from "./Transfer";
import { TransferCard } from "./TransferCard";

const TRANSFER: Transfer = {
  id: "t1",
  from_wallet_id: "w1",
  to_wallet_id: "w2",
  amount: "150.00",
  occurred_at: "2026-03-05T12:30:00Z",
  created_at: "2026-03-05T12:30:00Z",
  updated_at: null,
};

describe("TransferCard", () => {
  it("отображает все резолвленные поля карточки", () => {
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("Наличные → Карта")).toBeInTheDocument();
    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    expect(
      screen.getByText(dayjs(TRANSFER.occurred_at).format("DD.MM.YYYY HH:mm")),
    ).toBeInTheDocument();
  });

  it("рендерится без падения при нерезолвленных fromWalletName/toWalletName/currencyCode", () => {
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName={undefined}
        toWalletName={undefined}
        currencyCode={undefined}
        onEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("… → …")).toBeInTheDocument();
    expect(screen.getByText("150.00 …")).toBeInTheDocument();
  });

  it("нажатие на карточку вызывает onEdit с этим переводом", async () => {
    const onEdit = vi.fn();
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
        onEdit={onEdit}
      />,
    );

    await userEvent.click(screen.getByText("Наличные → Карта"));

    expect(onEdit).toHaveBeenCalledWith(TRANSFER);
  });

  it("Enter и пробел на карточке вызывают onEdit", async () => {
    const onEdit = vi.fn();
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
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
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
        onEdit={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Редактировать" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Удалить" })).not.toBeInTheDocument();
  });
});
