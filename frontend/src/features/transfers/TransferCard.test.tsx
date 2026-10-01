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
import type { Transfer } from "./Transfer";
import { TransferCard } from "./TransferCard";

const TEST_WORKSPACE_ID = "workspace-1";

const TRANSFER: Transfer = {
  id: "t1",
  from_wallet_id: "w1",
  to_wallet_id: "w2",
  currency_id: "cur1",
  amount: "150.00",
  occurred_at: "2026-03-05T12:30:00Z",
  created_at: "2026-03-05T12:30:00Z",
  updated_at: null,
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

describe("TransferCard", () => {
  it("отображает все резолвленные поля карточки", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("Наличные → Карта")).toBeInTheDocument();
    expect(screen.getByText("150.00 USD")).toBeInTheDocument();
    expect(
      screen.getByText(dayjs(TRANSFER.occurred_at).format("DD.MM.YYYY HH:mm")),
    ).toBeInTheDocument();
  });

  it("рендерится без падения при нерезолвленных fromWalletName/toWalletName/currencyCode", () => {
    const { wrapper } = setup(() => undefined);
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName={undefined}
        toWalletName={undefined}
        currencyCode={undefined}
        onEdit={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("… → …")).toBeInTheDocument();
    expect(screen.getByText("150.00 …")).toBeInTheDocument();
  });

  it("нажатие «Редактировать» вызывает onEdit с этим переводом", async () => {
    const { wrapper } = setup(() => undefined);
    const onEdit = vi.fn();
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
        onEdit={onEdit}
      />,
      { wrapper },
    );

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));

    expect(onEdit).toHaveBeenCalledWith(TRANSFER);
  });

  it("подтверждение в Popconfirm вызывает DELETE /api/transfers/{id}", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
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
            r.method === "DELETE" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transfers/t1`,
        ),
      ).toBe(true),
    );
  });

  it("отмена подтверждения не вызывает запрос", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(
      <TransferCard
        transfer={TRANSFER}
        fromWalletName="Наличные"
        toWalletName="Карта"
        currencyCode="USD"
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
