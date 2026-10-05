import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import type { Wallet } from "./Wallet";
import { WalletCard } from "./WalletCard";

const TEST_WORKSPACE_ID = "workspace-1";

const WALLET: Wallet = {
  id: "5",
  name: "Наличные",
  icon: "wallet",
  currency_id: "1",
  created_at: "2026-01-01T00:00:00Z",
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

describe("WalletCard", () => {
  it("отображает иконку, название и один чип валюты", () => {
    const { wrapper } = setup(() => undefined);
    render(<WalletCard wallet={WALLET} currencyCode="USD" onEdit={vi.fn()} />, {
      wrapper,
    });

    expect(document.querySelector('[data-icon="wallet"]')).toBeInTheDocument();
    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.getAllByText("USD")).toHaveLength(1);
  });

  it("пока код валюты неизвестен, чип не отображается", () => {
    const { wrapper } = setup(() => undefined);
    render(<WalletCard wallet={WALLET} currencyCode={undefined} onEdit={vi.fn()} />, { wrapper });

    expect(screen.getByText("Наличные")).toBeInTheDocument();
    expect(screen.queryByText("USD")).not.toBeInTheDocument();
  });

  it("нажатие «Редактировать» вызывает onEdit с этим кошельком", async () => {
    const { wrapper } = setup(() => undefined);
    const onEdit = vi.fn();
    render(<WalletCard wallet={WALLET} currencyCode="USD" onEdit={onEdit} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));

    expect(onEdit).toHaveBeenCalledWith(WALLET);
  });

  it("подтверждение в Popconfirm вызывает DELETE /api/workspaces/{workspace_id}/wallets/{id}", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(<WalletCard wallet={WALLET} currencyCode="USD" onEdit={vi.fn()} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some(
          (r) =>
            r.method === "DELETE" && r.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/5`,
        ),
      ).toBe(true),
    );
  });

  it("отмена подтверждения не вызывает запрос", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(<WalletCard wallet={WALLET} currencyCode="USD" onEdit={vi.fn()} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Отмена" }));

    expect(api.requests).toHaveLength(0);
  });
});
